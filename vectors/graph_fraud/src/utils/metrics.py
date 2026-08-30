"""
Evaluation metrics and utilities for the Blue Team models.
"""

from typing import Dict, Any

import torch
from sklearn.metrics import precision_recall_curve, precision_recall_fscore_support, roc_auc_score, confusion_matrix, average_precision_score
from torch_geometric.data import HeteroData
import torch.nn as nn

def find_optimal_threshold(model: nn.Module, data: HeteroData, head: str = 'node', search_split: str = 'train') -> float:
    """
    Finds the threshold that maximizes F1 score on the specified split.
    """
    model.eval()
    with torch.no_grad():
        node_out, edge_out = model(data.x_dict, data.edge_index_dict, 
                                   data[('account', 'transfer', 'account')].edge_attr,
                                   data['account'].x)

    if head == 'node':
        mask = data['account'][f'{search_split}_mask']
        y_true = data['account'].y[mask].cpu().numpy()
        probs = torch.softmax(node_out, dim=1)[:, 1][mask].detach().cpu().numpy()
    else:
        transfer_edge = ('account', 'transfer', 'account')
        mask = data[transfer_edge][f'{search_split}_mask']
        y_true = data[transfer_edge].edge_y[mask].cpu().numpy()
        probs = torch.softmax(edge_out, dim=1)[:, 1][mask].detach().cpu().numpy()

    if len(set(y_true)) < 2:
        return 0.5

    precision_arr, recall_arr, thresholds = precision_recall_curve(y_true, probs)
    f1_scores = 2 * (precision_arr * recall_arr) / (precision_arr + recall_arr + 1e-8)
    f1_scores = f1_scores[:-1]

    if len(f1_scores) == 0:
        return 0.5

    best_idx = f1_scores.argmax()
    return float(thresholds[best_idx])

def evaluate_nodes(model: nn.Module, data: HeteroData, split: str = 'test', threshold: float = None) -> Dict[str, float]:
    """
    Evaluates the node classification head (Mule detection).
    """
    model.eval()
    with torch.no_grad():
        node_out, _ = model(data.x_dict, data.edge_index_dict, 
                            data[('account', 'transfer', 'account')].edge_attr,
                            data['account'].x)

    mask = data['account'][f'{split}_mask']
    y_true = data['account'].y[mask].cpu().numpy()
    probs = torch.softmax(node_out, dim=1)[:, 1][mask].detach().cpu().numpy()

    if threshold is None:
        threshold = 0.5
    y_pred = (probs >= threshold).astype(int)

    if len(set(y_true)) > 1:
        auc = roc_auc_score(y_true, probs)
        pr_auc = average_precision_score(y_true, probs)
    else:
        auc = 0.0
        pr_auc = 0.0

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average='binary', zero_division=0
    )

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    return {'precision': precision, 'recall': recall, 'f1': f1, 
            'auc': auc, 'pr_auc': pr_auc, 'fpr': fpr, 'threshold': threshold}

def evaluate_edges(model: nn.Module, data: HeteroData, split: str = 'test', threshold: float = None) -> Dict[str, float]:
    """
    Evaluates the edge classification head (Fraud Transaction detection).
    """
    model.eval()
    with torch.no_grad():
        _, edge_out = model(data.x_dict, data.edge_index_dict, 
                            data[('account', 'transfer', 'account')].edge_attr,
                            data['account'].x)

    transfer_edge = ('account', 'transfer', 'account')
    mask = data[transfer_edge][f'{split}_mask']
    y_true = data[transfer_edge].edge_y[mask].cpu().numpy()
    probs = torch.softmax(edge_out, dim=1)[:, 1][mask].detach().cpu().numpy()

    if threshold is None:
        threshold = 0.5
    y_pred = (probs >= threshold).astype(int)

    if len(set(y_true)) > 1:
        auc = roc_auc_score(y_true, probs)
        pr_auc = average_precision_score(y_true, probs)
    else:
        auc = 0.0
        pr_auc = 0.0

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average='binary', zero_division=0
    )

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    return {'precision': precision, 'recall': recall, 'f1': f1,
            'auc': auc, 'pr_auc': pr_auc, 'fpr': fpr, 'threshold': threshold}

def get_predictions_for_evolution(model: nn.Module, data: HeteroData) -> Dict[str, Any]:
    """
    Get raw predictions and features for SmartEvolution analysis.
    Returns predictions, true labels, and features for both heads.
    """
    model.eval()
    with torch.no_grad():
        node_out, edge_out = model(data.x_dict, data.edge_index_dict, 
                                   data[('account', 'transfer', 'account')].edge_attr,
                                   data['account'].x)
        node_pred = node_out.argmax(dim=1).numpy()
        edge_pred = edge_out.argmax(dim=1).numpy()

        return {
            'node_pred': node_pred,
            'node_true': data['account'].y.cpu().numpy(),
            'node_features': data['account'].x.cpu().numpy(),
            'edge_pred': edge_pred,
            'edge_true': data[('account', 'transfer', 'account')].edge_y.cpu().numpy(),
            'edge_features': data[('account', 'transfer', 'account')].edge_attr.cpu().numpy()
        }
