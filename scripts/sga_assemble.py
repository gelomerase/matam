#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import re
import subprocess

if __name__ == '__main__':
    
    # Arguments parsing
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-i', '--input_fastq', metavar='FASTQ', 
                        type=str, required=True,
                        help='Input fastq file')
    parser.add_argument('-o', '--output_contigs', metavar='FASTA', 
                        type=str, default='contigs.fa',
                        help='Ouput contigs fasta file')
    parser.add_argument('--sga_bin', metavar='PATH', 
                        type=str, default='sga',
                        help='SGA bin path (by default sga is searched in $PATH)')
    parser.add_argument('--cpu', metavar='INT',
                        type=int, default=3,
                        help='Max number of CPU to use')
    args = parser.parse_args()
    
    # Preprocessing
    preprocess_output = 'preprocess_output.fq'
    
    cmd_line = args.sga_bin + ' preprocess -v ' + args.input_fastq
    cmd_line += ' -o ' + preprocess_output
    
    sys.stdout.write('CMD: {0}\n\n'.format(cmd_line))
    subprocess.call(cmd_line, shell=True)
    
    ## Error correction
    # Build the index that will be used for error correction
    cmd_line = args.sga_bin + ' index -a ropebwt' # ropebwt algo will only work for sequences < 200bp
    cmd_line += ' -t ' + str(args.cpu) + ' --no-reverse '
    cmd_line += preprocess_output
    
    sys.stdout.write('CMD: {0}\n'.format(cmd_line))
    subprocess.call(cmd_line, shell=True)
    
    # Perform error correction
    kmer_cutoff = 41
    error_corrected_output_basename = 'error_corrected'
    
    cmd_line = args.sga_bin + ' correct -k ' + str(kmer_cutoff)
    cmd_line += ' --discard -x 2 -t ' + str(args.cpu)
    cmd_line += ' -o ' + error_corrected_output_basename + '.fq'
    cmd_line += ' ' + preprocess_output
    
    sys.stdout.write('CMD: {0}\n\n'.format(cmd_line))
    subprocess.call(cmd_line, shell=True)
    
    ## Contig assembly
    # Index the corrected data
    cmd_line = args.sga_bin + ' index -a ropebwt' # ropebwt algo will only work for sequences < 200bp
    cmd_line += ' -t ' + str(args.cpu)
    cmd_line += ' ' + error_corrected_output_basename + '.fq'
    
    sys.stdout.write('CMD: {0}\n'.format(cmd_line))
    subprocess.call(cmd_line, shell=True)
    
    # Remove exact-match duplicates and reads with low-frequency k-mers
    filtered_output = error_corrected_output_basename + '.filter.pass.fa'
    min_kmer_coverage = 2
    
    cmd_line = args.sga_bin + ' filter -x ' + str(min_kmer_coverage)
    cmd_line += ' -t ' + str(args.cpu) + ' --homopolymer-check '
    cmd_line += '--low-complexity-check -o ' + filtered_output
    cmd_line += ' ' + error_corrected_output_basename + '.fq'
    
    sys.stdout.write('CMD: {0}\n'.format(cmd_line))
    subprocess.call(cmd_line, shell=True)
    
    # Merge simple, unbranched chains of vertices
    fm_merge_overlap = 55
    merged_output_basename = 'merged_output'
    
    cmd_line = args.sga_bin + ' fm-merge -m ' + str(fm_merge_overlap)
    cmd_line += ' -t ' + str(args.cpu) + ' -o ' + merged_output_basename + '.fa'
    cmd_line += ' ' + filtered_output
    
    sys.stdout.write('CMD: {0}\n'.format(cmd_line))
    subprocess.call(cmd_line, shell=True)
    
    # Build an index of the merged sequences
    cmd_line = args.sga_bin + ' index -d 1000000'
    cmd_line += ' -t ' + str(args.cpu)
    cmd_line += ' ' + merged_output_basename + '.fa'
    
    sys.stdout.write('CMD: {0}\n'.format(cmd_line))
    subprocess.call(cmd_line, shell=True)
    
    # Remove any substrings that were generated from the merge process
    cmd_line = args.sga_bin + ' rmdup'
    cmd_line += ' -t ' + str(args.cpu)
    cmd_line += ' ' + merged_output_basename + '.fa'
    
    sys.stdout.write('CMD: {0}\n'.format(cmd_line))
    subprocess.call(cmd_line, shell=True)
    
    # Compute the structure of the string graph
    min_overlap = fm_merge_overlap
    
    cmd_line = args.sga_bin + ' overlap -m ' + str(min_overlap)
    cmd_line += ' -t ' + str(args.cpu)
    cmd_line += ' ' + merged_output_basename + '.rmdup.fa'
    
    sys.stdout.write('CMD: {0}\n'.format(cmd_line))
    subprocess.call(cmd_line, shell=True)
    
    # Perform the contig assembly without bubble popping
    assembly_output_basename = 'assemble'
    
    cmd_line = args.sga_bin + ' assemble -m ' + str(min_overlap)
    cmd_line += ' -g 0 -d 0.03 -g 0.01 '
    cmd_line += ' --max-edges 10000 -b 3 -x 10 -l 50 '
    cmd_line += ' -o ' + assembly_output_basename
    cmd_line += ' ' + merged_output_basename + '.rmdup.asqg.gz'
    
    sys.stdout.write('CMD: {0}\n\n'.format(cmd_line))
    subprocess.call(cmd_line, shell=True)
    
    ## Final post-processing
    cmd_line = 'cp ' + assembly_output_basename + '-contigs.fa '
    cmd_line += args.output_contigs
    
    sys.stdout.write('CMD: {0}\n\n'.format(cmd_line))
    subprocess.call(cmd_line, shell=True)
    
    exit(0)