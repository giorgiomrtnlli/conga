######################################################################################88
import argparse
from os.path import exists
import sys
import os

parser = argparse.ArgumentParser()

parser.add_argument('--config', help="configuration file *.yml", type=str)
parser.add_argument('--output_clones_file')
parser.add_argument('--input_clones_file') # option to skip the 10x parsing if we already have a clones file
parser.add_argument('--organism', choices=['mouse', 'human', 'mouse_gd', 'human_gd', 'human_ig'], default = None)
#parser.add_argument('--n_components', type=int, default=50)
parser.add_argument('--filtered_contig_annotations_csvfile', help='Required unless --input_clones_file is present')
parser.add_argument('--consensus_annotations_csvfile', help='Not needed')
parser.add_argument('--no_tcrdists', action='store_true')
parser.add_argument('--no_kpca', action='store_true', help='Make the clones file '
                    'but dont compute the tcrdist distance matrix or run kernel PCA. '
                    'Useful for really large datasets; used in conjunction with '
                    'run_conga.py --no_kpca option')
parser.add_argument('--save_tcrdist_matrices', action='store_true')
parser.add_argument('--kpca_kernel')
parser.add_argument('--kpca_gaussian_kernel_sdev', default=100.0, type=float,
                    help='only used if kpca_kernel==\'gaussian\'')
parser.add_argument('--kpca_outfile')
parser.add_argument('--condense_clonotypes_by_tcrdist', action='store_true')
parser.add_argument('--tcrdist_threshold_for_condensing', type=float, default=50. )
parser.add_argument('--verbose', action='store_true')

args = parser.parse_args()

if len(sys.argv)==1:
    parser.print_help()
    sys.exit()

# update args specified in yml file
if args.config is not None:
    import yaml
    assert exists(args.config)
    yml_args = yaml.load(open(args.config), Loader=yaml.FullLoader)
    for k, v in yml_args.items():
        if k in args.__dict__:
            args.__dict__[k] = v
        else:
            sys.stderr.write("Ignored unknown parameter {} in yaml.\n".format(k))

if args.organism is None:
    print('Organism not specified. Add to --config file or specify with --organism')
    quit()

if args.input_clones_file is not None:
    assert exists(args.input_clones_file)
    assert exists(args.filtered_contig_annotations_csvfile is None) # doesn't make sense
else:
    assert exists(args.filtered_contig_annotations_csvfile)
    if args.consensus_annotations_csvfile is not None:
        assert exists(args.consensus_annotations_csvfile)

assert args.kpca_kernel in [None, 'gaussian'] #None means classic default

# put this after arg parsing because it's so dang slow
sys.path.append( os.path.dirname( os.path.dirname( os.path.abspath(__file__) ) ) ) # so we can import conga
import conga
from conga.preprocess import (make_tcrdist_kernel_pcs_file_from_clones_file,
                              condense_clones_file_and_barcode_mapping_file_by_tcrdist)

from conga.tcrdist.make_10x_clones_file import make_10x_clones_file


input_distfile = None

if args.input_clones_file is None:
    #### first make the clones file ####################################################
    stringent=True
    output_clones_file = args.filtered_contig_annotations_csvfile[:-4]+'_tcrdist_clones.tsv' \
                         if args.output_clones_file is None else args.output_clones_file
    #if args.condense_clonotypes_by_tcrdist:
    #    tmp_clones_filesuffix = '.uncondensed.tsv'
    #    output_clones_file += tmp_suffix # make a temporary version

    make_10x_clones_file(
        args.filtered_contig_annotations_csvfile,
        args.organism,
        output_clones_file,
        stringent=stringent,
        consensus_annotations_csvfile=args.consensus_annotations_csvfile,
        verbose=args.verbose
        )

    if args.condense_clonotypes_by_tcrdist:
        oldfile = output_clones_file
        output_clones_file = output_clones_file[:-4]+'_condensed.tsv'
        input_distfile = output_clones_file[:-4]+'_AB.dist'
        condense_clones_file_and_barcode_mapping_file_by_tcrdist(
            oldfile, output_clones_file, args.tcrdist_threshold_for_condensing, args.organism,
            output_distfile=input_distfile)


else:
    output_clones_file = args.input_clones_file

assert exists(output_clones_file)

#### Now compute the kernel PCs #######################################################

if args.no_tcrdists or args.no_kpca:
    print(f'Skipping TCRdist calculations and kernel PCA')
else:
    if args.save_tcrdist_matrices:
        output_distfile = output_clones_file[:-4]+'_AB.dist'
    else:
        output_distfile = None

    make_tcrdist_kernel_pcs_file_from_clones_file(
        output_clones_file,
        args.organism,
        kernel=args.kpca_kernel,
        outfile=args.kpca_outfile,
        gaussian_kernel_sdev=args.kpca_gaussian_kernel_sdev,
        input_distfile=input_distfile,
        output_distfile=output_distfile,
    )

print(f'If this all worked you should be able to pass {output_clones_file} as the --clones_file argument to run_conga.py')
print('DONE')

