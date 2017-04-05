"""
@author: Mirko Polato
@contact: mpolato@math.unipd.it
@organization: University of Padua
"""

import scipy.misc as miscs
from scipy.special import binom
import utils as ut
from utils.misc import bignom, Binomemoize
from cvxopt.lapack import syev
import numpy as np
import cvxopt as co
import math
import mpmath as mp


def linear(X, norm=True):
	K = X.T * X
	
	if norm:
		for i in range(K.size[0]):
			if K[i,i] == 0:
				K[i,i] = 1.0
				
	return ut.kernels.normalize(K) if norm else K
	

def normalize(K):
	"""
	@param K: the matrix
	@type K: cvxopt dense matrix
	@return: the row-normalized matrix
	@rtype: cvxopt dense matrix
	"""
	YY = ut.cvx.diagonal_vec(K)
	YY = co.sqrt(YY)**(-1)
	return co.mul(K, YY*YY.T)


def spectral_complexity(K):
	a = ut.cvx.trace(K)
	b = np.linalg.norm(K, "fro")
	return a / b


def spectral_complexity_norm(K):
	return (spectral_complexity(K) - 1.0) / (np.sqrt(K.size[0]) - 1.0)


def tanimoto(X, norm=False):
	d = co.matrix([sum(X[:,i].V) for i in xrange(X.size[1])])
	Yp = ut.ones_vec(X.size[1]) * d.T
	Xp = d * ut.ones_vec(X.size[1]).T
	Kl = X.T * X
	K = co.div(Kl, Xp + Yp - Kl)
	return ut.kernels.normalize(K) if norm else K


def sparse_polynomial(X, c=1.0, d=2):
	K = X.T * X
	S = co.spmatrix(0.0, [], [], K.size)
	for i in range(1, d+1):
		cmb = miscs.comb(d, i)
		A = co.spmatrix(K.V**i, K.I, K.J)
		S += cmb * c**(d-i) * A
		
	return S
	

def polynomial(X, c=0.0, d=2.0, norm=True):
	K = ((X.T * X) + c)**d
	return ut.kernels.normalize(K) if norm else K


@ut.timing
def d_kernel(R, k, norm=True):
	
	n, m = R.size
	
	x_choose_k = [0]*(n+1)
	for i in range(1, n+1):
		x_choose_k[i] = binom(i,k)
	
	nCk = x_choose_k[n]
	X = R.T*R
	
	K = co.matrix(0.0, (X.size[0], X.size[1]))
	for i in range(m):
		#if (i+1) % 100 == 0:
		#	print "%d/%d" %(i+1,m)
		for j in range(i, m):
			n_niCk = x_choose_k[n-int(X[i,i])]
			n_njCk = x_choose_k[n-int(X[j,j])]
			n_ni_nj_nijCk = x_choose_k[n+int(-X[i,i] - X[j,j] + X[i,j])]
			K[i,j] = K[j,i] = nCk - n_niCk - n_njCk + n_ni_nj_nijCk
	
	if norm:
		for i in range(m):
			if K[i,i] == 0:
				K[i,i] = 1.0
				
	return ut.kernels.normalize(K) if norm else K

@ut.timing
def c_kernel(R, k, norm=True):
	
	n, m = R.size
	X = R.T*R

	x_choose_k = [0]*(n+1)
	for i in range(1, n+1):
		x_choose_k[i] = binom(i,k)

	K = co.matrix(0.0, (m,m))
	for i in range(m):
		for j in range(i, m):
			K[i,j] = K[j,i] = x_choose_k[int(X[i,j])]
			
	if norm:
		for i in range(m):
			if K[i,i] == 0:
				K[i,i] = 1.0
				
		K = ut.kernels.normalize(K)		
	return K


@ut.timing
def all_dnf_kernel(R, k, d, norm=True):

	n, m = R.size
	X = R.T*R
	
	C = binom(2**d*int(binom(n, d)), k) - 2*binom((2**d-1)*int(binom(n, d)), k)
	N = (2**d-2)*int(binom(n, d))
	
	U = co.matrix(1.0, (n,1))
	K = co.matrix(0.0, (m,m))
	for i in range(m):
		if (i+1) % 100 == 0:
			print "%d/%d" %(i+1,m)
		for j in range(i, m):
			nij = int(X[i,j]) + ((U - R[:,i]).T*((U - R[:,j])))[0]
			K[i,j] = K[j,i] = C + binom(N + binom(nij, d), k) 
	
	if norm:
		for i in range(m):
			if K[i,i] == 0:
				K[i,i] = 1.0
				
	return ut.kernels.normalize(K)	if norm else K
		
			
@ut.timing
def dnf_kernel(R, k, s, norm=True):
		
	n, m = R.size
	
	x_choose_s = {n : bignom(n,s)}
	nCs = x_choose_s[n]
	
	x_choose_k = {nCs : bignom(nCs,k)}
	a = x_choose_k[nCs]
	
	X = R.T*R
	
	if k == s == 1:
		K = X
	else:
		K = co.matrix(0.0, (m, m))
		for i in range(m):
			if (i+1) % 100 == 0:
				print "%d/%d" %(i+1,m)
			
			for j in range(i, m):
				
				xii = int(X[i,i])
				if xii not in x_choose_s:
					x_choose_s[xii] = bignom(xii, s)
				nCs_niCs = nCs - x_choose_s[xii]
				
				if nCs_niCs not in x_choose_k:
					x_choose_k[nCs_niCs] = bignom(nCs_niCs, k)
				b = x_choose_k[nCs_niCs]
				
				xjj = int(X[j,j])
				if xjj not in x_choose_s:
					x_choose_s[xjj] = bignom(xjj, s)
				nCs_njCs = nCs - x_choose_s[xjj]
				
				if nCs_njCs not in x_choose_k:
					x_choose_k[nCs_njCs] = bignom(nCs_njCs, k)
				c = x_choose_k[nCs_njCs]
				
				xij = int(X[i,j])
				if xij not in x_choose_s:
					x_choose_s[xij] = bignom(xij, s)
				nCs_niCs_njCs_nijCs = nCs - x_choose_s[xii] - x_choose_s[xjj] + x_choose_s[xij]
				
				if nCs_niCs_njCs_nijCs not in x_choose_k:
					x_choose_k[nCs_niCs_njCs_nijCs] = bignom(nCs_niCs_njCs_nijCs, k)
				d = x_choose_k[nCs_niCs_njCs_nijCs]
				
				K[i,j] = K[j,i] = float(a - c + d - b)
	
	if norm:
		for i in range(m):
			if K[i,i] == 0:
				K[i,i] = 1.0
				
		K = ut.kernels.normalize(K)	
	
	return K
	

@ut.timing
def mdnf_kernel(R, norm=True):
	
	n, m = R.size
	X = R.T*R

	K = co.matrix(0.0, (m,m))
	for i in range(m):
		for j in range(i, m):
			K[i,j] = K[j,i] = 2.0**int(X[i,j]) - 1.0
			
	return ut.kernels.normalize(K) if norm else K



#TESTING STUFF
@ut.timing
def mdnf_kernel_norm(R):
	
	n, m = R.size
	X = R.T*R

	d = {i : mp.mpf(2**int(X[i,i]) - 1) for i in range(m)}
	
	K = co.matrix(0.0, (m,m))
	for i in range(m):
		if (i+1) % 100 == 0:
			print "%d/%d" %(i+1,m)
		for j in range(i+1, m):
			K[i,j] = K[j,i] = float(mp.mpf(2**int(X[i,j]) - 1) / (mp.sqrt(d[i])*mp.sqrt(d[j])))
			
	for i in range(m):
		K[i,i] = 1.0	
		
	return K


'''
EXPERIMENTAL PART
'''

def k_over_d(k, d, bin, n, nij, ni_nij, nj_nij, n_ni_nj_nij):
	
	if k == 0:
		return bin.go(n, d)

	A1 = 0
	for s in range(k):
		A1 += bin.go(nij, s) * bin.go(ni_nij, k-s-1) * bin.go(nj_nij, k-s-1) * bin.go(n_ni_nj_nij, d+s-2*(k-1))
		  
	A2 = 0
	for s in range(k):
		D = 0
		for t in range(k-s, d-k+2):
			D += bin.go(ni_nij, t) * bin.go(n_ni_nj_nij, d-t-k+1)
		A2 += bin.go(nij, s) * bin.go(nj_nij, k-s-1) * D

	A3 = 0        
	for s in range(k):
		D = 0
		for t in range(k-s, d-k+2):
			D += bin.go(nj_nij, t) * bin.go(n_ni_nj_nij, d-t-k+1)
		A3 += bin.go(nij, s) * bin.go(ni_nij, k-s-1) * D

	return k_over_d(k-1, d, bin, n, nij, ni_nij, nj_nij, n_ni_nj_nij) - A1 - A2 - A3


@ut.timing
def kd_kernel(R, d, k, norm=True):

	n, m = R.size
	X = R.T*R
	
	bin = Binomemoize()
	
	K = co.matrix(0.0, (m,m))
	for i in range(m):
		if (i+1) % 100 == 0:
			print "%d/%d" %(i+1,m)
		for j in range(i, m):
			K[i,j] = K[j,i] = k_over_d(k, d, bin, n, int(X[i,j]), int(X[i,i] - X[i,j]), int(X[j,j] - X[i,j]), n+int(-X[i,i] - X[j,j] + X[i,j]))
			
	if norm:
		for i in range(m):
			if K[i,i] == 0:
				K[i,i] = 1.0
		
		K = ut.kernels.normalize(K)		
	return K


def k_over_d_back(k, d, bin, n, nij, ni_nij, nj_nij, n_ni_nj_nij):
		
	if k == d:
		return bin.go(nij, d)

	A1 = 0
	for s in range(k+1):
		A1 += bin.go(nij, s) * bin.go(ni_nij, k-s) * bin.go(nj_nij, k-s) * bin.go(n_ni_nj_nij, d+s-2*k)
		  
	A2 = 0
	for s in range(k+1):
		D = 0
		for t in range(k-s+1, d-s+1):
			D += bin.go(ni_nij, t) * bin.go(n_ni_nj_nij, d-t-k)
		A2 += bin.go(nij, s) * bin.go(nj_nij, k-s) * D

	A3 = 0        
	for s in range(k+1):
		D = 0
		for t in range(k-s+1, d-s+1):
			D += bin.go(nj_nij, t) * bin.go(n_ni_nj_nij, d-t-k)
		A3 += bin.go(nij, s) * bin.go(ni_nij, k-s) * D

	return k_over_d_back(k+1, d, bin, n, nij, ni_nij, nj_nij, n_ni_nj_nij) + A1 + A2 + A3
		
		
@ut.timing
def kd_kernel_back(R, d, k, norm=True):

	n, m = R.size
	X = R.T*R
	
	bin = Binomemoize()
	
	K = co.matrix(0.0, (m,m))
	for i in range(m):
		if (i+1) % 100 == 0:
			print "%d/%d" %(i+1,m)
		for j in range(i, m):
			K[i,j] = K[j,i] = k_over_d_back(k, d, bin, n, int(X[i,j]), int(X[i,i] - X[i,j]), int(X[j,j] - X[i,j]), n+int(-X[i,i] - X[j,j] + X[i,j]))
			
	if norm:
		for i in range(m):
			if K[i,i] == 0:
				K[i,i] = 1.0
		
		K = ut.kernels.normalize(K)		
	return K

def ekd_kernel(R, k, d, norm=True):
	n, m = R.size
	X = R.T*R
	
	bin = Binomemoize()
	K = co.matrix(0.0, (m,m))
	for i in range(m):
		if (i+1) % 100 == 0:
			print "%d/%d" %(i+1,m)
		for j in range(i, m):
			for s in range(k+1):
				K[i,j] += bin.go(int(X[i,j]), s) * bin.go(int(X[i,i] - X[i,j]), k-s) * bin.go(int(X[j,j] - X[i,j]), k-s) * bin.go(n-int(X[j,j])-int(X[i,i])+int(X[i,j]), d-2*k+s)
			K[j,i] = K[i,j]
	
	if norm:
		for i in range(m):
			if K[i,i] == 0:
				K[i,i] = 1.0
		
		K = ut.kernels.normalize(K)	
	
	return K

def ekd_comb_kernel(R, d, norm=True):
	n, m = R.size
	K = co.matrix(0.0, (m,m))
	for k in range(1,d+1):
		K += ekd_kernel(R, k, d, False)
		
	return ut.kernels.normalize(K)	if norm else K
	
'''
END OF EXPERIMENTAL PART
'''
