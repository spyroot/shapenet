# Mustafa Bayramov
import numpy as np
import networkx as nx
import torch

# use pytorch dataloader
from ..adjacency_encoder import AdjacencyEncoder
from ..adjacency_flexible_encoder import AdjacencyFlexEncoder
from ...models.sampler.utils import bfs_paths


class GraphSeqSampler(torch.utils.data.Dataset):
    """
    Graph Dataset Sampler,  sampled batch of graph and return
    a batch , each sample is dict that hold key 'x', 'y', len.

    The y computed by performing BFS order traversal based
    on random starting node.
    """

    def __init__(self, graphs, max_nodes=None, max_depth=None, max_iter=20000, is_sorted=False):

        # sorted or not
        self.sorted = is_sorted
        #
        self.A = []
        #
        self.len_all = []
        # max iteration
        self._max_iter = max_iter
        #
        self.k = 10

        for g in graphs:
            self.A.append(np.asarray(nx.to_numpy_matrix(g)))
            self.len_all.append(g.number_of_nodes())

        self.n = max_nodes
        self.depth = max_depth

        if max_nodes is None or max_nodes == 0:
            self.n = max(self.len_all)

        if max_depth is None or max_depth == 0:
            self.depth = max(self.compute_max_depth())

        if self.sorted:
            self.depth = max_depth
            len_batch_order = np.argsort(np.array(self.len_all))[::-1]
            self.len_all = [self.len_all[i] for i in len_batch_order]
            self.A = [self.A[i] for i in len_batch_order]

        self.encoder = AdjacencyEncoder(depth=self.depth)
        self.base_encoder = AdjacencyFlexEncoder(depth=self.depth)

    def __len__(self):
        """
        @return:
        """
        # if self.depth is None or self.depth == 0:
        #     self.n = max(self.len_all)
        #     print("Len COMPUTED MAX NODE DEPTH", self.n)
        #
        # if self.depth is None or self.depth == 0:
        #     self.depth = max(self.compute_max_depth())
        #     print("Len COMPUTED MAX DEPTH", self.depth)

        return len(self.A)

    def __getitem__(self, idx):
        """
         Return training batch
         @return: x, y and len batch as dict 'x', 'y', 'len'
        """
        # if self.n is None or self.n == 0:
        #     self.n = max(self.len_all)
        #     print("Get Item COMPUTED MAX NODE DEPTH", self.n)
        #
        # if self.depth is None or self.depth == 0:
        #     self.depth = max(self.compute_max_depth())
        #     print("Get Item COMPUTED MAX DEPTH", self.depth)

        A = self.A[idx].copy()

        # pad
        x_batch = np.zeros((self.n, self.depth))
        x_batch[0, :] = 1

        # true y batch
        y_batch = np.zeros((self.n, self.depth))

        # generate input x, y pairs
        batch_len = A.shape[0]
        # permutation of ids
        permuted_xs = np.random.permutation(A.shape[0])
        A = A[np.ix_(permuted_xs, permuted_xs)]
        # convert, it does not make a copy if
        # the input is already a matrix
        # or an ndarray
        adj_copy_matrix = np.asmatrix(A)

        # we do bfs so some random start node
        bfs_paths_id = np.array(bfs_paths(nx.from_numpy_matrix(adj_copy_matrix),
                                          np.random.randint(A.shape[0])))

        # now we encode and shift.
        A = A[np.ix_(bfs_paths_id, bfs_paths_id)]
        A_encoded = self.encoder.encode(A.copy(), depth=self.depth)
        y_batch[0:A_encoded.shape[0], :] = A_encoded
        x_batch[1:A_encoded.shape[0] + 1, :] = A_encoded
        return {'x': x_batch, 'y': y_batch, 'len': batch_len}

    def compute_max_depth(self):
        """
        Computes max depth for input graph.
        @return:
        """
        depth = []
        k = self.k

        for _ in range(self._max_iter):
            adj_idx = np.random.randint(len(self.A))
            A = self.A[adj_idx].copy()

            permuted_xs = np.random.permutation(A.shape[0])
            A = A[np.ix_(permuted_xs, permuted_xs)]
            adj_copy_matrix = np.asmatrix(A)

            # then do bfs in the permuted G
            bfs_ids = np.array(bfs_paths(nx.from_numpy_matrix(adj_copy_matrix),
                                         np.random.randint(A.shape[0])))
            A = A[np.ix_(bfs_ids, bfs_ids)]

            # encode adj
            adj_encoded = AdjacencyFlexEncoder.encode(A.copy())
            max_encoded_len = max([len(adj_encoded[i]) for i in range(len(adj_encoded))])
            depth.append(max_encoded_len)

        depth = sorted(depth)[-1 * k:]
        return depth
