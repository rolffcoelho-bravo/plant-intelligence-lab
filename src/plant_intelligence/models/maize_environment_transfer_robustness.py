"""Case Study B6-R: robustness of continuous-environment transfer.

The B5 outer folds remain unchanged. A small pre-registered grid is selected
inside each outer training set using the other four frozen environment folds.
Selection uses additive G+E RMSE only. The chosen representation is then reused
for the product GxE challenger and all strict genotype folds associated with
that held-out environment fold.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.stats import spearmanr
from sklearn.decomposition import PCA
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

from plant_intelligence.data.maize_environment_transfer import acquire_source, load_source
from plant_intelligence.models.maize_environment_transfer import (
    BOOTSTRAP_REPS, G_SKETCH_DIM, MARKER_CHUNK, SEED, FeatureMap,
    _attach_folds, _countsketch_assignments, _load_manifests, _safe_corr,
    _sqeuclidean, prepare_cells, tensor_features,
)


@dataclass(frozen=True)
class TransferConfig:
    name: str
    g_rank: int
    e_rank: int
    gamma_multiplier: float
    alpha: float


GRID = (
    TransferConfig("baseline", 20, 16, 1.0, 10.0),
    TransferConfig("environment_broader", 20, 16, 0.5, 10.0),
    TransferConfig("environment_narrower", 20, 16, 2.0, 10.0),
    TransferConfig("environment_rank_8", 20, 8, 1.0, 10.0),
    TransferConfig("environment_rank_32", 20, 32, 1.0, 10.0),
    TransferConfig("genomic_rank_10", 10, 16, 1.0, 10.0),
    TransferConfig("genomic_rank_40", 40, 16, 1.0, 10.0),
    TransferConfig("ridge_3", 20, 16, 1.0, 3.0),
    TransferConfig("ridge_30", 20, 16, 1.0, 30.0),
)
BASE = GRID[0]
MAX_G_RANK = 40


def metrics(y, p):
    return {
        "rmse": float(np.sqrt(mean_squared_error(y, p))),
        "mae": float(mean_absolute_error(y, p)),
        "r2": float(r2_score(y, p)),
        "correlation": _safe_corr(np.asarray(y), np.asarray(p)),
    }


def load_materialized(root: Path):
    raw = root / "data" / "raw" / "case_study_b5_g2f"
    paths = {n: raw / n for n in ("PHENO.csv", "GENO.csv", "ECOV.csv")}
    if not all(p.exists() for p in paths.values()):
        paths, _ = acquire_source(root)
    return load_source(paths)


def genomic_map(geno, id_col, train_ids, rank=MAX_G_RANK):
    ids = tuple(geno[id_col].astype(str))
    lookup = {v: i for i, v in enumerate(ids)}
    tr = np.asarray([lookup[v] for v in sorted(train_ids) if v in lookup], dtype=int)
    n_markers = geno.shape[1] - 1
    buckets, signs = _countsketch_assignments(n_markers)
    sketch = np.zeros((len(ids), G_SKETCH_DIM), dtype=np.float32)
    for start in range(0, n_markers, MARKER_CHUNK):
        stop = min(start + MARKER_CHUNK, n_markers)
        block = geno.iloc[:, 1 + start:1 + stop].apply(pd.to_numeric, errors="coerce").to_numpy(np.float32)
        means = np.nanmean(block[tr], axis=0)
        stds = np.nanstd(block[tr], axis=0)
        means = np.where(np.isfinite(means), means, 0.0).astype(np.float32)
        stds = np.where(np.isfinite(stds) & (stds > 1e-6), stds, 1.0).astype(np.float32)
        miss = ~np.isfinite(block)
        if miss.any():
            rr, cc = np.where(miss)
            block[rr, cc] = means[cc]
        block = (block - means) / stds
        proj = csr_matrix((signs[start:stop], (np.arange(stop-start), buckets[start:stop])),
                          shape=(stop-start, G_SKETCH_DIM), dtype=np.float32)
        sketch += np.asarray(block @ proj, dtype=np.float32)
    z = StandardScaler().fit(sketch[tr]).transform(sketch).astype(np.float32)
    pca = PCA(n_components=rank, random_state=SEED).fit(z[tr])
    val = pca.transform(z).astype(np.float32) / np.sqrt(rank)
    return FeatureMap(ids, val, {"feature_dim": rank, "pca_explained_variance": float(pca.explained_variance_ratio_.sum())})


def sliced(fmap: FeatureMap, rank: int):
    old = fmap.values.shape[1]
    val = fmap.values[:, :rank].copy() * np.sqrt(old / rank)
    return FeatureMap(fmap.ids, val.astype(np.float32), {**fmap.metadata, "feature_dim": rank})


def environment_map(ecov, train_ids, rank, gamma_multiplier):
    ids = tuple(ecov.index.astype(str))
    lookup = {v: i for i, v in enumerate(ids)}
    tr = np.asarray([lookup[v] for v in sorted(train_ids)], dtype=int)
    x = ecov.to_numpy(float)
    scaler = StandardScaler().fit(x[tr])
    z = scaler.transform(x)
    ztr = z[tr]
    d2 = _sqeuclidean(ztr, ztr)
    upper = d2[np.triu_indices_from(d2, 1)]
    positive = upper[upper > 1e-12]
    med = float(np.median(positive)) if len(positive) else 1.0
    gamma = gamma_multiplier / max(med, 1e-12)
    k = np.exp(-gamma * d2)
    vals, vecs = np.linalg.eigh(k)
    order = np.argsort(vals)[::-1]
    vals, vecs = vals[order], vecs[:, order]
    keep = min(rank, int(np.sum(vals > 1e-10)))
    vals, vecs = vals[:keep], vecs[:, :keep]
    kall = np.exp(-gamma * _sqeuclidean(z, ztr))
    phi = (kall @ (vecs / np.sqrt(vals)[None, :])).astype(np.float32) / np.sqrt(keep)
    return FeatureMap(ids, phi, {"feature_dim": keep, "rbf_gamma": gamma, "gamma_multiplier": gamma_multiplier})


def cell_features(cells, gmap, emap):
    gi, ei = gmap.lookup(), emap.lookup()
    g = np.vstack([gmap.values[gi[str(v)]] for v in cells["genotype"]]).astype(np.float32)
    e = np.vstack([emap.values[ei[str(v)]] for v in cells["environment"]]).astype(np.float32)
    return g, e


def predict(spec, tg, te, y, vg, ve, alpha):
    if spec == "G":
        xt, xv = tg, vg
    elif spec == "G+E":
        xt, xv = np.hstack([tg, te]), np.hstack([vg, ve])
    elif spec == "G+E+GxE":
        xt = np.hstack([tg, te, tensor_features(tg, te)])
        xv = np.hstack([vg, ve, tensor_features(vg, ve)])
    else:
        raise ValueError(spec)
    sc = StandardScaler().fit(xt)
    model = Ridge(alpha=alpha, solver="lsqr").fit(sc.transform(xt), y)
    return model.predict(sc.transform(xv))


def choose(metrics_df):
    order = {c.name: i for i, c in enumerate(GRID)}
    w = metrics_df.copy()
    w["order"] = w["config"].map(order)
    return str(w.sort_values(["inner_rmse", "order"]).iloc[0]["config"])


def config(name):
    return next(c for c in GRID if c.name == name)


def tune(outer, cells, gmax, ecov):
    train_outer = cells[cells.environment_fold != outer]
    inner_folds = sorted(train_outer.environment_fold.unique())
    rows = []
    cache = {}
    for cfg in GRID:
        errs, abs_errs, fold_rmses = [], [], []
        gm = sliced(gmax, cfg.g_rank)
        for inner in inner_folds:
            tr = train_outer[train_outer.environment_fold != inner]
            va = train_outer[train_outer.environment_fold == inner]
            key = (int(inner), cfg.e_rank, cfg.gamma_multiplier)
            if key not in cache:
                cache[key] = environment_map(ecov, set(tr.environment), cfg.e_rank, cfg.gamma_multiplier)
            em = cache[key]
            tg, te = cell_features(tr, gm, em)
            vg, ve = cell_features(va, gm, em)
            p = predict("G+E", tg, te, tr.observed.to_numpy(float), vg, ve, cfg.alpha)
            err = va.observed.to_numpy(float) - p
            errs.append(err * err); abs_errs.append(np.abs(err)); fold_rmses.append(np.sqrt(np.mean(err*err)))
        sq, ae = np.concatenate(errs), np.concatenate(abs_errs)
        rows.append({"outer_environment_fold": int(outer), "config": cfg.name,
                     "g_rank": cfg.g_rank, "e_rank": cfg.e_rank,
                     "gamma_multiplier": cfg.gamma_multiplier, "alpha": cfg.alpha,
                     "inner_rmse": float(np.sqrt(sq.mean())), "inner_mae": float(ae.mean()),
                     "inner_fold_rmse_sd": float(np.std(fold_rmses, ddof=1))})
    out = pd.DataFrame(rows)
    selected = choose(out)
    out["selected"] = out.config.eq(selected)
    return out, config(selected)


def novelty(ecov, train_ids, test_ids, gamma_multiplier):
    ids = list(ecov.index.astype(str)); ix = {v:i for i,v in enumerate(ids)}
    trn, tst = sorted(train_ids), sorted(test_ids)
    tr = np.asarray([ix[v] for v in trn]); ts = np.asarray([ix[v] for v in tst])
    x = ecov.to_numpy(float); sc = StandardScaler().fit(x[tr])
    ztr, zts = sc.transform(x[tr]), sc.transform(x[ts])
    d2tr = _sqeuclidean(ztr, ztr)
    up = d2tr[np.triu_indices_from(d2tr, 1)]; pos = up[up > 1e-12]
    med = float(np.median(pos)) if len(pos) else 1.0
    gamma = gamma_multiplier / max(med, 1e-12)
    d2 = _sqeuclidean(zts, ztr); d = np.sqrt(d2); k = min(5, d.shape[1])
    return pd.DataFrame({"environment": tst,
        "novelty_nearest_z": d.min(axis=1),
        "novelty_mean5_z": np.mean(np.partition(d, k-1, axis=1)[:, :k], axis=1),
        "max_training_kernel_similarity": np.exp(-gamma*d2.min(axis=1))})


def add_pred(store, test, regime, scenario, label, pred, cfg_name):
    f = test[["genotype","environment","observed","environment_fold","genotype_fold"]].copy()
    f["regime"], f["scenario"], f["model"], f["predicted"], f["selected_config"] = regime, scenario, label, pred, cfg_name
    store.append(f)


def run_models(root: Path):
    pheno, geno, ecov = load_materialized(root)
    cells, geno, ecov, cols = prepare_cells(pheno, geno, ecov)
    envm, genom = _load_manifests(root / "reports" / "results")
    cells = _attach_folds(cells, envm, genom)
    preds, sels, novs, selected = [], [], [], {}

    for outer in sorted(envm.environment_fold.unique()):
        tr = cells[cells.environment_fold != outer]; te = cells[cells.environment_fold == outer]
        gmax = genomic_map(geno, cols["geno_id"], set(tr.genotype))
        sm, cfg = tune(int(outer), cells, gmax, ecov); sels.append(sm); selected[int(outer)] = cfg
        gm, em = sliced(gmax, cfg.g_rank), environment_map(ecov, set(tr.environment), cfg.e_rank, cfg.gamma_multiplier)
        bg, be = sliced(gmax, BASE.g_rank), environment_map(ecov, set(tr.environment), BASE.e_rank, BASE.gamma_multiplier)
        tg, tE = cell_features(tr, gm, em); vg, vE = cell_features(te, gm, em)
        btg, btE = cell_features(tr, bg, be); bvg, bvE = cell_features(te, bg, be)
        y = tr.observed.to_numpy(float); scn = f"efold_{outer}"
        for spec,label in (("G","Selected-G"),("G+E","Selected-G+E"),("G+E+GxE","Selected-G+E+GxE")):
            add_pred(preds, te, "CV-E-continuous-B6R", scn, label, predict(spec,tg,tE,y,vg,vE,cfg.alpha), cfg.name)
        add_pred(preds, te, "CV-E-continuous-B6R", scn, "B6-fixed-G+E", predict("G+E",btg,btE,y,bvg,bvE,BASE.alpha), BASE.name)
        nv = novelty(ecov, set(tr.environment), set(te.environment), cfg.gamma_multiplier)
        nv["regime"], nv["environment_fold"], nv["selected_config"] = "CV-E-continuous-B6R", int(outer), cfg.name
        novs.append(nv)

    strict_g = {}
    for gf in sorted(genom.genotype_fold.unique()):
        ids = set(genom.loc[genom.genotype_fold != gf, "genotype"].astype(str))
        strict_g[int(gf)] = genomic_map(geno, cols["geno_id"], ids)
    for outer,cfg in selected.items():
        train_envs = set(envm.loc[envm.environment_fold != outer, "environment"].astype(str))
        em = environment_map(ecov, train_envs, cfg.e_rank, cfg.gamma_multiplier)
        be = environment_map(ecov, train_envs, BASE.e_rank, BASE.gamma_multiplier)
        for gf,gmax in strict_g.items():
            tr = cells[(cells.environment_fold != outer)&(cells.genotype_fold != gf)]
            te = cells[(cells.environment_fold == outer)&(cells.genotype_fold == gf)]
            if te.empty: continue
            gm,bg = sliced(gmax,cfg.g_rank), sliced(gmax,BASE.g_rank)
            tg,tE = cell_features(tr,gm,em); vg,vE = cell_features(te,gm,em)
            btg,btE = cell_features(tr,bg,be); bvg,bvE = cell_features(te,bg,be)
            y=tr.observed.to_numpy(float); scn=f"efold_{outer}__gfold_{gf}"
            for spec,label in (("G","Selected-G"),("G+E","Selected-G+E"),("G+E+GxE","Selected-G+E+GxE")):
                add_pred(preds,te,"CV-GE-continuous-B6R",scn,label,predict(spec,tg,tE,y,vg,vE,cfg.alpha),cfg.name)
            add_pred(preds,te,"CV-GE-continuous-B6R",scn,"B6-fixed-G+E",predict("G+E",btg,btE,y,bvg,bvE,BASE.alpha),BASE.name)
        test_envs=set(envm.loc[envm.environment_fold == outer,"environment"].astype(str))
        nv=novelty(ecov,train_envs,test_envs,cfg.gamma_multiplier)
        nv["regime"],nv["environment_fold"],nv["selected_config"]="CV-GE-continuous-B6R",outer,cfg.name
        novs.append(nv)
    return pd.concat(preds,ignore_index=True), pd.concat(sels,ignore_index=True), pd.concat(novs,ignore_index=True)


def summaries(preds, nov):
    pooled=[]
    for (r,m),p in preds.groupby(["regime","model"]): pooled.append({"regime":r,"model":m,"n":len(p),**metrics(p.observed,p.predicted)})
    env=[]
    for (r,e,m),p in preds.groupby(["regime","environment","model"]): env.append({"regime":r,"environment":e,"environment_fold":int(p.environment_fold.iloc[0]),"model":m,"n":len(p),"selected_config":p.selected_config.iloc[0],**metrics(p.observed,p.predicted)})
    env=pd.DataFrame(env).merge(nov.drop_duplicates(["regime","environment"]),on=["regime","environment","environment_fold","selected_config"],how="left")
    diag=[]
    for (r,m),p in env.groupby(["regime","model"]):
        s=spearmanr(p.novelty_mean5_z,p.rmse); n=spearmanr(p.novelty_nearest_z,p.rmse)
        q1,q3=np.quantile(p.novelty_mean5_z,[.25,.75]); lo=p.loc[p.novelty_mean5_z<=q1,"rmse"].mean(); hi=p.loc[p.novelty_mean5_z>=q3,"rmse"].mean()
        diag.append({"regime":r,"model":m,"n_environments":len(p),"spearman_mean5_novelty_vs_rmse":float(s.statistic),"spearman_mean5_pvalue":float(s.pvalue),"spearman_nearest_novelty_vs_rmse":float(n.statistic),"spearman_nearest_pvalue":float(n.pvalue),"low_novelty_quartile_mean_rmse":float(lo),"high_novelty_quartile_mean_rmse":float(hi),"high_minus_low_quartile_rmse":float(hi-lo)})
    return pd.DataFrame(pooled), env, pd.DataFrame(diag)


def bootstrap(preds,reps=BOOTSTRAP_REPS):
    comps=(("Selected-G+E","Selected-G"),("Selected-G+E+GxE","Selected-G+E"),("Selected-G+E","B6-fixed-G+E")); rng=np.random.default_rng(SEED+61); rows=[]
    for r,p in preds.groupby("regime"):
        q=p.pivot_table(index=["genotype","environment","observed"],columns="model",values="predicted",aggfunc="first").reset_index(); envs=np.asarray(sorted(q.environment.unique()))
        for ch,ref in comps:
            a=(q.observed-q[ch])**2; b=(q.observed-q[ref])**2; st=pd.DataFrame({"environment":q.environment,"a":a,"b":b}).groupby("environment").agg(sa=("a","sum"),sb=("b","sum"),n=("a","size")); d=[]
            for _ in range(reps):
                sm=rng.choice(envs,len(envs),replace=True); z=st.loc[sm]; nn=z.n.sum(); d.append(np.sqrt(z.sa.sum()/nn)-np.sqrt(z.sb.sum()/nn))
            rows.append({"regime":r,"challenger":ch,"reference":ref,"metric":"RMSE","delta_challenger_minus_reference":float(np.sqrt(a.mean())-np.sqrt(b.mean())),"ci95_low":float(np.quantile(d,.025)),"ci95_high":float(np.quantile(d,.975)),"improvement_frequency":float(np.mean(np.asarray(d)<0)),"bootstrap_clusters":"environment","bootstrap_reps":reps})
    return pd.DataFrame(rows)


def figure(env,diag,path):
    f=env[env.model=="Selected-G+E"]; fig,ax=plt.subplots(figsize=(11.8,6.7))
    for r,mark,label in (("CV-E-continuous-B6R","o","Unseen environment"),("CV-GE-continuous-B6R","^","Unseen genotype + environment")):
        p=f[f.regime==r]; ax.scatter(p.novelty_mean5_z,p.rmse,s=32,alpha=.72,marker=mark,label=label)
        if len(p)>1:
            c=np.polyfit(p.novelty_mean5_z,p.rmse,1); xx=np.linspace(p.novelty_mean5_z.min(),p.novelty_mean5_z.max(),100); ax.plot(xx,c[0]*xx+c[1],lw=1.2)
    text=[]
    for _,z in diag[diag.model=="Selected-G+E"].iterrows(): text.append(("CV-E" if z.regime.startswith("CV-E-") else "CV-GE")+f": Spearman ρ={z.spearman_mean5_novelty_vs_rmse:.3f}")
    ax.text(.015,.985,"\n".join(text),transform=ax.transAxes,va="top",fontsize=9); ax.set_xlabel("Environmental novelty: mean distance to 5 nearest training environments"); ax.set_ylabel("Environment-level RMSE"); ax.set_title("Case Study B6-R — environmental novelty versus transfer error"); ax.grid(alpha=.2)
    fig.legend(loc="lower center",ncol=2,frameon=False,bbox_to_anchor=(.5,.01)); fig.tight_layout(rect=(0,.09,1,1)); path.parent.mkdir(parents=True,exist_ok=True); fig.savefig(path,dpi=180,bbox_inches="tight"); plt.close(fig)


def run(output_root: Path):
    root=output_root.resolve(); res=root/"reports"/"results"; figs=root/"reports"/"figures"; res.mkdir(parents=True,exist_ok=True)
    preds,sels,nov=run_models(root); pooled,env,diag=summaries(preds,nov); boot=bootstrap(preds); selected=sels[sels.selected].sort_values("outer_environment_fold")
    out={"summary":res/"case_study_b6r_transfer_summary.csv","selection":res/"case_study_b6r_nested_selection.csv","selected":res/"case_study_b6r_selected_configs.csv","environment_errors":res/"case_study_b6r_environment_errors.csv","novelty":res/"case_study_b6r_novelty_diagnostics.csv","bootstrap":res/"case_study_b6r_bootstrap.csv","figure":figs/"case_study_b6r_novelty_vs_error.png"}
    pooled.to_csv(out["summary"],index=False); sels.to_csv(out["selection"],index=False); selected.to_csv(out["selected"],index=False); env.to_csv(out["environment_errors"],index=False); diag.to_csv(out["novelty"],index=False); boot.to_csv(out["bootstrap"],index=False); figure(env,diag,out["figure"]); return out


def main():
    p=argparse.ArgumentParser(); p.add_argument("--output-root",default="."); a=p.parse_args(); out=run(Path(a.output_root)); print("Case Study B6-R complete"); [print(f"{k}: {v}") for k,v in out.items()]


if __name__ == "__main__": main()
