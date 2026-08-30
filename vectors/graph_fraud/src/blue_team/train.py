"""
Training loop and loss functions for the Blue Team GNN.
"""

import logging
from typing import Dict, Any

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import HeteroData

# Absolute imports based on our package structure
from src.utils.metrics import evaluate_nodes, evaluate_edges

logger = logging.getLogger(__name__)

class FocalLoss(nn.Module):
    """Down-weights easy examples so training focuses on the hard, rare fraud cases."""
    def __init__(self, alpha: torch.Tensor = None, gamma: float = 2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """Focal loss for one batch."""
        ce_loss = F.cross_entropy(logits, targets, weight=self.alpha, reduction='none')
        probs = torch.softmax(logits, dim=1)
        p_t = probs.gather(1, targets.unsqueeze(1)).squeeze(1)
        focal_term = (1.0 - p_t).clamp(min=1e-8) ** self.gamma
        loss = focal_term * ce_loss
        return loss.mean()

def train_model(model: nn.Module, data: HeteroData, epochs: int = None,
                lr: float = 0.01, weight_decay: float = 5e-4,
                node_weight_cap: float = 5.0, edge_weight_cap: float = 10.0,
                focal_gamma: float = 2.0) -> nn.Module:
    """
    Trains the DualHeadHGTDetector using Focal Loss and Early Stopping.
    """
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)

    # Scale inner epochs with graph size for better Edge Head convergence
    transfer_edge = ('account', 'transfer', 'account')
    if epochs is None:
        n_edges = data[transfer_edge].edge_index.shape[1] if transfer_edge in data.edge_index_dict else data.edge_index.shape[1]
        if n_edges < 10000:
            epochs = 120
        elif n_edges < 30000:
            epochs = 150
        else:
            epochs = 180
        logger.info(f"   \U0001f4d0 Auto-scaled inner epochs to {epochs} (graph has {n_edges} edges)")

    # ─── Node Class Weights ───
    train_mask = data['account'].train_mask
    labels = data['account'].y
    n_legit_nodes = (labels[train_mask] == 0).sum().item()
    n_mule_nodes = max((labels[train_mask] == 1).sum().item(), 1)
    raw_node_ratio = n_legit_nodes / n_mule_nodes
    node_weights = torch.FloatTensor([1.0, min(node_weight_cap, raw_node_ratio)])

    # ─── Edge Class Weights ───
    e_train_mask = data[transfer_edge].train_mask
    e_labels = data[transfer_edge].edge_y
    n_legit_edges = (e_labels[e_train_mask] == 0).sum().item()
    n_fraud_edges = max((e_labels[e_train_mask] == 1).sum().item(), 1)
    raw_edge_ratio = n_legit_edges / n_fraud_edges
    edge_weights = torch.FloatTensor([1.0, min(edge_weight_cap, raw_edge_ratio)])

    edge_focal_loss = FocalLoss(alpha=edge_weights, gamma=focal_gamma)

    logger.info(f"⚖️ Class Weights (capped: node≤{node_weight_cap}x, edge≤{edge_weight_cap}x):")
    logger.info(f"   Node: Legit={node_weights[0]:.2f}, Mule={node_weights[1]:.2f} (raw ratio: {raw_node_ratio:.1f}x)")
    logger.info(f"   Edge: Legit={edge_weights[0]:.2f}, Fraud={edge_weights[1]:.2f} (raw ratio: {raw_edge_ratio:.1f}x)")

    best_val_score = 0.0
    best_model_state = None
    patience = 15
    no_improve = 0

    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()

        x_dict = data.x_dict
        edge_index_dict = data.edge_index_dict
        edge_attr = data[transfer_edge].edge_attr
        raw_account_x = data['account'].x
        
        node_out, edge_out = model(x_dict, edge_index_dict, edge_attr, raw_account_x)

        node_loss = F.cross_entropy(
            node_out[train_mask],
            labels[train_mask],
            weight=node_weights
        )

        edge_loss = edge_focal_loss(
            edge_out[e_train_mask],
            e_labels[e_train_mask]
        )

        total_loss = node_loss + edge_loss
        total_loss.backward()
        optimizer.step()

        if (epoch + 1) % 10 == 0:
            val_node = evaluate_nodes(model, data, 'val')
            val_edge = evaluate_edges(model, data, 'val')
            combined_f1 = (val_node['f1'] + val_edge['f1']) / 2

            logger.info(
                f"Epoch {epoch+1:3d} | Loss: {total_loss.item():.4f} | "
                f"Node F1: {val_node['f1']:.3f} | Edge F1: {val_edge['f1']:.3f} | "
                f"Combined: {combined_f1:.3f}"
            )

            if combined_f1 > best_val_score:
                best_val_score = combined_f1
                best_model_state = {k: v.clone() for k, v in model.state_dict().items()}
                no_improve = 0
            else:
                no_improve += 10

            if no_improve >= patience:
                logger.info(f"⏹️ Early stopping at epoch {epoch+1}")
                break

    if best_model_state:
        model.load_state_dict(best_model_state)
        logger.info(f"✅ Loaded best model (Combined F1: {best_val_score:.4f})")

    return model
