"""
Dual-Head Heterogeneous Graph Transformer (HGT) for Mule & Cross-Rail Detection.
"""

import logging
from typing import Tuple, Dict, Any

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import HGTConv, Linear
from torch_geometric.data import HeteroData

logger = logging.getLogger(__name__)

# =====================================================================
# NODE FEATURE COLUMN INDICES
# =====================================================================
NODE_FEAT_IN_DEGREE: int = 1
NODE_FEAT_OUT_DEGREE: int = 2
NODE_FEAT_PAGERANK: int = 3
GRAPH_CONTEXT_DIM: int = 4 

class DualHeadHGTDetector(nn.Module):
    """
    Dual-Head HGT: 
    Backbone: HGTConv layers (Heterogeneous Graph Transformer)
    Head 1:   Linear(account_emb → is_mule)
    Head 2:   MLP(sender_emb + receiver_emb + edge_features + graph_context → is_fraud)
    """
    def __init__(self, metadata: Tuple[list, list], in_channels_dict: Dict[str, int], 
                 edge_in_channels: int, hidden_channels: int = 64, 
                 num_heads: int = 4, num_layers: int = 2):
        super().__init__()
        
        self.lin_dict = nn.ModuleDict()
        for node_type in metadata[0]:
            in_channels = in_channels_dict.get(node_type, 1)
            self.lin_dict[node_type] = Linear(in_channels, hidden_channels)

        self.convs = nn.ModuleList()
        for _ in range(num_layers):
            conv = HGTConv(hidden_channels, hidden_channels, metadata, num_heads)
            self.convs.append(conv)
            
        self.dropout = nn.Dropout(0.3)

        # Node Head (Account Mule Detection)
        self.node_head = nn.Linear(hidden_channels, 2)

        # Edge Head (Cross-Rail Transfer Detection)
        edge_input_dim = hidden_channels * 2 + edge_in_channels + GRAPH_CONTEXT_DIM
        self.edge_head = nn.Sequential(
            nn.Linear(edge_input_dim, 32),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(32, 2)
        )

    def get_embeddings(self, x_dict: Dict[str, torch.Tensor], 
                       edge_index_dict: Dict[Tuple[str, str, str], torch.Tensor]) -> Dict[str, torch.Tensor]:
        # Project all node features to hidden_channels
        """Node embeddings after message passing, shared by both heads."""
        x_dict_proj = {
            node_type: self.lin_dict[node_type](x).relu_()
            for node_type, x in x_dict.items()
        }
        
        # Apply HGT layers
        for conv in self.convs:
            x_dict_proj = conv(x_dict_proj, edge_index_dict)
            # Apply relu/dropout to all node types
            x_dict_proj = {k: self.dropout(F.relu(v)) for k, v in x_dict_proj.items()}
            
        return x_dict_proj

    def forward(self, x_dict: Dict[str, torch.Tensor], 
                edge_index_dict: Dict[Tuple[str, str, str], torch.Tensor], 
                transfer_edge_attr: torch.Tensor, 
                raw_account_x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        
        """Node-level (mule) and edge-level (cross-rail) predictions."""
        embeddings = self.get_embeddings(x_dict, edge_index_dict)
        account_emb = embeddings['account']
        
        # Node classification (only on account nodes)
        node_out = self.node_head(account_emb)
        
        # Edge classification (only on 'transfer' edges)
        transfer_edge_index = edge_index_dict[('account', 'transfer', 'account')]
        src_idx = transfer_edge_index[0]
        dst_idx = transfer_edge_index[1]
        
        src_emb = account_emb[src_idx]
        dst_emb = account_emb[dst_idx]
        
        # Graph context directly from original features
        src_out_deg = raw_account_x[src_idx, NODE_FEAT_OUT_DEGREE:NODE_FEAT_OUT_DEGREE + 1]
        dst_in_deg = raw_account_x[dst_idx, NODE_FEAT_IN_DEGREE:NODE_FEAT_IN_DEGREE + 1]
        src_pagerank = raw_account_x[src_idx, NODE_FEAT_PAGERANK:NODE_FEAT_PAGERANK + 1]
        dst_pagerank = raw_account_x[dst_idx, NODE_FEAT_PAGERANK:NODE_FEAT_PAGERANK + 1]
        
        graph_context = torch.cat(
            [src_out_deg, dst_in_deg, src_pagerank, dst_pagerank], dim=1
        )
        
        edge_input = torch.cat([src_emb, dst_emb, transfer_edge_attr, graph_context], dim=1)
        edge_out = self.edge_head(edge_input)
        
        return node_out, edge_out

def build_model(data: HeteroData, hidden_channels: int = 64, 
                num_heads: int = 4, num_layers: int = 2) -> DualHeadHGTDetector:
    """
    Factory function to instantiate the Dual-Head HGT Model from a PyG HeteroData object.
    """
    transfer_edge_attr_dim = data['account', 'transfer', 'account'].edge_attr.size(1)
    
    in_channels_dict = {
        node_type: data[node_type].x.size(1) for node_type in data.metadata()[0]
    }
    
    model = DualHeadHGTDetector(
        metadata=data.metadata(),
        in_channels_dict=in_channels_dict,
        edge_in_channels=transfer_edge_attr_dim,
        hidden_channels=hidden_channels,
        num_heads=num_heads,
        num_layers=num_layers
    )
    
    logger.info("🧠 HGT Model Architecture initialized.")
    total_params = sum(p.numel() for p in model.parameters())
    logger.info(f"Total parameters: {total_params:,}")
    return model
