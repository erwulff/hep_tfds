import pickle
import bz2

import numpy as np
from numpy.lib.recfunctions import append_fields

CMS_PF_CLASS_NAMES = ["none" "charged hadron", "neutral hadron", "hfem", "hfhad", "photon", "electron", "muon"]

ELEM_LABELS_CMS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
ELEM_NAMES_CMS = ["NONE", "TRACK", "PS1", "PS2", "ECAL", "HCAL", "GSF", "BREM", "HFEM", "HFHAD", "SC", "HO"]

CLASS_LABELS_CMS = [0, 211, 130, 1, 2, 22, 11, 13]
CLASS_NAMES_CMS = ["none", "ch.had", "n.had", "HFEM", "HFHAD", "gamma", "ele", "mu"]

X_FEATURES = [
    "typ_idx", "pt", "eta", "phi", "e",
    "layer", "depth", "charge", "trajpoint", 
    "eta_ecal", "phi_ecal", "eta_hcal", "phi_hcal", "muon_dt_hits", "muon_csc_hits", "muon_type",
    "px", "py", "pz", "deltap", "sigmadeltap", "gsf_electronseed_trkorecal", "num_hits", "cluster_flags", "corr_energy"
]
               
Y_FEATURES = [
    "typ_idx",
    "charge",
    "pt",
    "eta",
    "sin_phi",
    "cos_phi",
    "e",
]

def prepare_data_cms(fn, padded_num_elem_size):
    Xs = []
    ygens = []
    ycands = []

    if fn.endswith(".pkl"):
        data = pickle.load(open(fn, "rb"), encoding="iso-8859-1")
    elif fn.endswith(".pkl.bz2"):
        data = pickle.load(bz2.BZ2File(fn, "rb"))

    for event in data:
        Xelem = event["Xelem"]
        ygen = event["ygen"]
        ycand = event["ycand"]

        # remove PS from inputs, they don't seem to be very useful
        msk_ps = (Xelem["typ"] == 2) | (Xelem["typ"] == 3)

        Xelem = Xelem[~msk_ps]
        ygen = ygen[~msk_ps]
        ycand = ycand[~msk_ps]

        Xelem = append_fields(
            Xelem, "typ_idx", np.array([ELEM_LABELS_CMS.index(int(i)) for i in Xelem["typ"]], dtype=np.float32)
        )
        ygen = append_fields(
            ygen, "typ_idx", np.array([CLASS_LABELS_CMS.index(abs(int(i))) for i in ygen["typ"]], dtype=np.float32)
        )
        ycand = append_fields(
            ycand,
            "typ_idx",
            np.array([CLASS_LABELS_CMS.index(abs(int(i))) for i in ycand["typ"]], dtype=np.float32),
        )

        Xelem_flat = np.stack(
            [
                Xelem[k].view(np.float32).data
                for k in X_FEATURES
            ],
            axis=-1,
        )
        ygen_flat = np.stack(
            [
                ygen[k].view(np.float32).data
                for k in Y_FEATURES
            ],
            axis=-1,
        )
        ycand_flat = np.stack(
            [
                ycand[k].view(np.float32).data
                for k in Y_FEATURES
            ],
            axis=-1,
        )

        # take care of outliers
        Xelem_flat[np.isnan(Xelem_flat)] = 0
        Xelem_flat[np.abs(Xelem_flat) > 1e4] = 0
        ygen_flat[np.isnan(ygen_flat)] = 0
        ygen_flat[np.abs(ygen_flat) > 1e4] = 0
        ycand_flat[np.isnan(ycand_flat)] = 0
        ycand_flat[np.abs(ycand_flat) > 1e4] = 0

        X = Xelem_flat[:padded_num_elem_size]
        X = np.pad(X, [(0, padded_num_elem_size - X.shape[0]), (0, 0)])

        ygen = ygen_flat[:padded_num_elem_size]
        ygen = np.pad(ygen, [(0, padded_num_elem_size - ygen.shape[0]), (0, 0)])

        ycand = ycand_flat[:padded_num_elem_size]
        ycand = np.pad(ycand, [(0, padded_num_elem_size - ycand.shape[0]), (0, 0)])

        X = np.expand_dims(X, 0)
        ygen = np.expand_dims(ygen, 0)
        ycand = np.expand_dims(ycand, 0)

        Xs.append(X)
        ygens.append(ygen)
        ycands.append(ycand)

    X = [np.concatenate(Xs)]
    ygen = [np.concatenate(ygens)]
    ycand = [np.concatenate(ycands)]

    return X, ygen, ycand

def split_sample(path, pad_size, test_frac=0.8):
        files = sorted(list(path.glob("*.pkl*")))
        idx_split = int(test_frac*len(files))
        files_train = files[:idx_split]
        files_test = files[idx_split:]
        return {"train": generate_examples(files_train, pad_size), "test": generate_examples(files_test, pad_size)}

def generate_examples(files, pad_size):
    """Yields examples."""

    for fi in files:
        X, ygen, ycand = prepare_data_cms(str(fi), pad_size)
        for ii in range(X[0].shape[0]):
            x = X[0][ii]
            yg = ygen[0][ii]
            yc = ycand[0][ii]
            yield str(fi) + "_" + str(ii), {
                "X": x,
                "ygen": yg,
                "ycand": yc,
            }

