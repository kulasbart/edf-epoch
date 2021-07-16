#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import numpy as np
import pandas as pd
pd.set_option('precision', 6)
import io
import regex as re
import argparse
import re

from helpers import EDFReader

debug=False

def padtrim(buf, num):
	num -= len(buf)
	if num>=0:
		if isinstance(buf,str):
			buffer = (buf + ' ' * num)
			buffer = bytes(buffer, 'latin-1')
		else:
			# pad the input to the specified length
			buffer = (buf + bytes('', 'latin-1') * num)
	else:
		# trim the input to the specified length
		buffer = (buf[0:num])
		if isinstance(buffer,str):
			buffer = bytes(buffer, 'latin-1')
	
	return buffer

if debug:
	class Namespace:
		def __init__(self, **kwargs):
			self.__dict__.update(kwargs)
	
	data_fname = '/media/veracrypt6/projects/eplink/walkthrough_example/ieeg_sample/input/EPL31_LHS_0010/EPL31_LHS_0010_01_SE05_IEEG_CS/sub-EPL31LHS0010_ses-V01SE06_task-full_run-01_ieeg.edf'
	start_time = 10
	end_time= 500
	args = Namespace(data_fname=data_fname, start_time=start_time, end_time=end_time)

def main(args):
	
	out_fname = os.path.splitext(args.data_fname)[0]+'_epoch.edf'
	
	#read in the file
	file_in = EDFReader()
	header = file_in.open(args.data_fname)
	
	# determine the annoation data block index
	tal_indx = [i for i,x in enumerate(header['chan_info']['ch_names']) if x.endswith('Annotations')][0]
	
	# determine the size of the data block
	blocksize = np.sum(header['chan_info']['n_samps']) * header['meas_info']['data_size']
	start_block = int(args.start_time/header['meas_info']['record_length'])
	end_block = int((args.end_time)/header['meas_info']['record_length'])
	
	# obtain annoation start index
	tal_start=np.sum([x for i,x in enumerate(header['chan_info']['n_samps']) if i !=tal_indx])* header['meas_info']['data_size']
	
	hdr=bytearray(header['meas_info']['data_offset'])
	with open(args.data_fname, 'rb') as fid:
		fid.seek(0, io.SEEK_SET)
		fid.readinto(hdr)
	
	# update header with new data block size
	hdr[236:244]=padtrim(str(end_block-start_block),len(hdr[236:244]))
	
	# write the header info so new edf file
	with open(out_fname, "wb") as file_out:
		file_out.write(hdr)
	
	print('\n')
	print('Slicing data...')
	
	update_cnt = start_block+int((end_block-start_block)/10)
	start_time_adjust=args.start_time+float(header['meas_info']['record_length'])
	pat = '([+-]\\d+\\.?\\d*)\x14'
	for iblock in range(start_block, end_block):
		blockMap = bytearray(blocksize)
		with open(args.data_fname, 'rb') as fid:
			fid.seek(header['meas_info']['data_offset']+(iblock*blocksize), io.SEEK_SET)
			fid.readinto(blockMap)
		
		raw = re.findall(pat, blockMap[tal_start:].decode('latin-1'))
		
		new_block=[]
		for iraw in raw:
			if len(str(header['meas_info']['record_length']))==6:
				update_time=bytes('{0:.4f}'.format((float(iraw)-start_time_adjust)+float(header['meas_info']['record_length'])),'latin-1')
			else:
				update_time=bytes('{0:.3f}'.format((float(iraw)-start_time_adjust)+float(header['meas_info']['record_length'])),'latin-1')
			
			if new_block:
				new_block = bytearray(re.sub(bytes(str(float(iraw)),'latin-1'),update_time,new_block))
			else:
				new_block = bytearray(re.sub(bytes(str(float(iraw)),'latin-1'),update_time,blockMap[tal_start:]))
		
		if len(new_block) < len(blockMap[tal_start:]):
			new_block=new_block+(bytes('\x00','latin-1')*(len(blockMap[tal_start:])-len(new_block)))
		elif len(new_block) > len(blockMap[tal_start:]):
			new_block=new_block[0:(len(blockMap[tal_start:])-len(new_block))]
			
		with open(out_fname, "ab") as file_out:
			file_out.write(blockMap[:tal_start]+new_block)
		
		if iblock == update_cnt and iblock < end_block-1:
			print('{}%'.format(int((update_cnt/end_block)*100)))
			update_cnt += int((end_block-start_block)/10)

if __name__ == "__main__":

	# Input arguments
	parser = argparse.ArgumentParser()
	parser.add_argument('-i', '--data_fname', help='Path to original EDF file.', required=True)
	parser.add_argument('-s', '--start_time', type=float, help='Start time of epoch (seconds).', required=True)
	parser.add_argument('-e', '--end_time', type=float, help='End time of epoch (seconds).')
	args = parser.parse_args()

	main(args)