"""
Graph construction utilities. 
Converts DataFrames to NetworkX graphs and then to PyTorch Geometric HeteroData objects.
"""

import logging
from typing import Dict, Any, Tuple

import pandas as pd
import networkx as nx
import numpy as np
import torch
from torch_geometric.data import HeteroData

import config

logger = logging.getLogger(__name__)

def build_networkx_graph(edges_df: pd.DataFrame, nodes_df: pd.DataFrame) -> nx.MultiDiGraph:
    """
    Build a Directed Multi-Graph using NetworkX.
    Nodes = Accounts
    Edges = Transactions
    """
    logger.info("Building Directed Multi-Graph...")
    G = nx.MultiDiGraph()
    
    # 1. Add Nodes with properties
    logger.info("  -> Adding Nodes...")
    for _, row in nodes_df.iterrows():
        G.add_node(
            row['account_id'],
            account_type=row['account_type'],
            account_age=row['account_age_days'],
            device_hash=row['device_hash'],
            ip_subnet=row['ip_subnet'],
            is_mule=row['is_mule']
        )
        
    # 2. Add Edges with properties
    logger.info("  -> Adding Edges...")
    for _, row in edges_df.iterrows():
        G.add_edge(
            row['sender'],
            row['receiver'],
            txn_id=row['txn_id'],
            amount=row['amount'],
            rail=row['rail'],
            dwell_time=row['dwell_time_seconds'],
            is_structured=row['is_structured'],
            shared_hash=row['shared_hash'],
            is_fraud=row['is_fraud'],
            timestamp=row['timestamp']
        )
        
    logger.info(f"✅ Graph built: {G.number_of_nodes()} Nodes, {G.number_of_edges()} Edges")
    return G

def compute_graph_features(G: nx.MultiDiGraph, nodes_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute structural features for each node and append to DataFrame.
    """
    logger.info("Computing Graph-Level Features (This may take a moment)...")
    
    # Ensure graph acts as a simple DiGraph for structural metrics
    G_simple = nx.DiGraph(G)
    
    # 1. Degree Centrality
    logger.info("  -> Computing In/Out Degrees...")
    in_degrees = dict(G_simple.in_degree())
    out_degrees = dict(G_simple.out_degree())
    
    # 2. PageRank
    logger.info("  -> Computing PageRank...")
    pagerank = nx.pagerank(G_simple, weight='amount')
    
    # 3. Community Detection (Weak Components)
    logger.info("  -> Computing Connectivity components...")
    wcc = list(nx.weakly_connected_components(G_simple))
    wcc_size = {node: len(comp) for comp in wcc for node in comp}

    # Map features back to the Node DataFrame
    nodes_df['in_degree'] = nodes_df['account_id'].map(in_degrees).fillna(0)
    nodes_df['out_degree'] = nodes_df['account_id'].map(out_degrees).fillna(0)
    nodes_df['pagerank'] = nodes_df['account_id'].map(pagerank).fillna(0)
    nodes_df['wcc_size'] = nodes_df['account_id'].map(wcc_size).fillna(1)
    
    # 4. Compute 'device_shared_count'
    logger.info("  -> Computing Device & IP sharing signals...")
    device_counts = nodes_df['device_hash'].value_counts().to_dict()
    nodes_df['device_shared_count'] = nodes_df['device_hash'].map(device_counts)
    
    ip_counts = nodes_df['ip_subnet'].value_counts().to_dict()
    nodes_df['ip_shared_count'] = nodes_df['ip_subnet'].map(ip_counts)

    return nodes_df

def prepare_for_gnn(nodes_df: pd.DataFrame, edges_df: pd.DataFrame, use_hgt: bool = False) -> Dict[str, Any]:
    """
    Prepare the final feature matrices required by PyTorch Geometric (PyG).
    """
    logger.info(f"Formatting data for PyTorch Geometric (GNN, Heterogeneous={use_hgt})...")
    
    node_mapping = {acc: i for i, acc in enumerate(nodes_df['account_id'].unique())}
    
    # 1. Edge Index
    source_nodes = edges_df['sender'].map(node_mapping).values
    target_nodes = edges_df['receiver'].map(node_mapping).values
    edge_index = np.vstack((source_nodes, target_nodes))
    
    # 2. Node Features (Normalize numeric columns)
    feature_cols = list(config.NODE_FEATURE_NAMES)
    
    X_nodes = nodes_df[feature_cols].copy()
    for col in feature_cols:
        X_nodes[col] = (X_nodes[col] - X_nodes[col].min()) / (X_nodes[col].max() - X_nodes[col].min() + 1e-9)
        
    node_features = X_nodes.values
    node_labels = nodes_df['is_mule'].values
    
    # 3. Edge Features
    edge_cols = list(config.EDGE_FEATURE_NAMES)
    X_edges = edges_df[edge_cols].copy()
    # Velocity feature
    X_edges['velocity'] = edges_df['amount'] / (edges_df['dwell_time_seconds'] + 1)
    
    # Also normalize velocity
    for col in edge_cols + ['velocity']:
        X_edges[col] = (X_edges[col] - X_edges[col].min()) / (X_edges[col].max() - X_edges[col].min() + 1e-9)
    
    edge_features = X_edges.values
    edge_labels = edges_df['is_fraud'].values

    if use_hgt:
        device_mapping = {dev: i for i, dev in enumerate(nodes_df['device_hash'].unique())}
        ip_mapping = {ip: i for i, ip in enumerate(nodes_df['ip_subnet'].unique())}
        
        acc_nodes_for_device = nodes_df['account_id'].map(node_mapping).values
        dev_nodes = nodes_df['device_hash'].map(device_mapping).values
        edge_index_uses_device = np.vstack((acc_nodes_for_device, dev_nodes))
        
        acc_nodes_for_ip = nodes_df['account_id'].map(node_mapping).values
        ip_nodes = nodes_df['ip_subnet'].map(ip_mapping).values
        edge_index_uses_ip = np.vstack((acc_nodes_for_ip, ip_nodes))
        
        graph_data = {
            'heterogeneous': True,
            'node_features_account': node_features,
            'node_labels_account': node_labels,
            'num_nodes_device': len(device_mapping),
            'num_nodes_ip': len(ip_mapping),
            'edge_index_transfer': edge_index,
            'edge_features_transfer': edge_features,
            'edge_labels_transfer': edge_labels,
            'edge_index_uses_device': edge_index_uses_device,
            'edge_index_uses_ip': edge_index_uses_ip,
            'node_mapping': node_mapping
        }
    else:
        graph_data = {
            'heterogeneous': False,
            'edge_index': edge_index,
            'node_features': node_features,
            'node_labels': node_labels,
            'edge_features': edge_features,
            'edge_labels': edge_labels,
            'node_mapping': node_mapping
        }
    
    logger.info("✅ PyTorch Geometric data package created.")
    return graph_data

def build_pyg_data(gnn_data: Dict[str, Any]) -> HeteroData:
    """Convert our dict to a PyTorch Geometric HeteroData object."""
    data = HeteroData()

    # --- Node Features & Labels ---
    data['account'].x = torch.FloatTensor(gnn_data['node_features_account'])
    data['account'].y = torch.LongTensor(gnn_data['node_labels_account'])
    
    num_devices = gnn_data['num_nodes_device']
    num_ips = gnn_data['num_nodes_ip']
    
    data['device'].x = torch.ones((num_devices, 1))
    data['ip'].x = torch.ones((num_ips, 1))
    
    # --- Edges ---
    data['account', 'transfer', 'account'].edge_index = torch.LongTensor(gnn_data['edge_index_transfer'])
    data['account', 'transfer', 'account'].edge_attr = torch.FloatTensor(gnn_data['edge_features_transfer'])
    data['account', 'transfer', 'account'].edge_y = torch.LongTensor(gnn_data['edge_labels_transfer'])
    
    data['account', 'uses', 'device'].edge_index = torch.LongTensor(gnn_data['edge_index_uses_device'])
    data['account', 'uses', 'ip'].edge_index = torch.LongTensor(gnn_data['edge_index_uses_ip'])
    
    # Add reverse edges
    rev_dev = data['account', 'uses', 'device'].edge_index.flip([0])
    data['device', 'used_by', 'account'].edge_index = rev_dev
    
    rev_ip = data['account', 'uses', 'ip'].edge_index.flip([0])
    data['ip', 'used_by', 'account'].edge_index = rev_ip

    num_acc_nodes = data['account'].num_nodes
    num_edges = data['account', 'transfer', 'account'].edge_index.shape[1]

    # ─── Node Split (60/20/20) ───
    node_idx = np.random.permutation(num_acc_nodes)
    n_train = int(0.6 * num_acc_nodes)
    n_val = int(0.8 * num_acc_nodes)

    node_train_mask = np.zeros(num_acc_nodes, dtype=bool)
    node_val_mask = np.zeros(num_acc_nodes, dtype=bool)
    node_test_mask = np.zeros(num_acc_nodes, dtype=bool)
    node_train_mask[node_idx[:n_train]] = True
    node_val_mask[node_idx[n_train:n_val]] = True
    node_test_mask[node_idx[n_val:]] = True

    data['account'].train_mask = torch.BoolTensor(node_train_mask)
    data['account'].val_mask = torch.BoolTensor(node_val_mask)
    data['account'].test_mask = torch.BoolTensor(node_test_mask)

    # ─── Edge Split (60/20/20) ───
    edge_idx = np.random.permutation(num_edges)
    e_train = int(0.6 * num_edges)
    e_val = int(0.8 * num_edges)

    edge_train_mask = np.zeros(num_edges, dtype=bool)
    edge_val_mask = np.zeros(num_edges, dtype=bool)
    edge_test_mask = np.zeros(num_edges, dtype=bool)
    edge_train_mask[edge_idx[:e_train]] = True
    edge_val_mask[edge_idx[e_train:e_val]] = True
    edge_test_mask[edge_idx[e_val:]] = True

    transfer_edge = ('account', 'transfer', 'account')
    data[transfer_edge].train_mask = torch.BoolTensor(edge_train_mask)
    data[transfer_edge].val_mask = torch.BoolTensor(edge_val_mask)
    data[transfer_edge].test_mask = torch.BoolTensor(edge_test_mask)

    return data

def rebuild_graph_from_epoch_data(epoch_df: pd.DataFrame, accounts_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Take an epoch's transaction DataFrame → build graph → compute features →
    return PyG-ready dataset.
    """
    G = build_networkx_graph(epoch_df, accounts_df)
    nodes_featured = compute_graph_features(G, accounts_df.copy())
    gnn_data = prepare_for_gnn(nodes_featured, epoch_df, use_hgt=config.USE_HGT)
    return gnn_data
