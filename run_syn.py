
import argparse 

from data.datasets import *
from models.methods import run_conformal, weighted_conformal_prediction
from models import utils
from datetime import datetime
import random

def get_config():
    parser = argparse.ArgumentParser(description='Transductive Conformal Prediction')

    # Data settings
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--save_path', type=str, default='./results')
    parser.add_argument('--debug', type=bool, default=True)
    parser.add_argument('--dataset', type=str, default='cevae')

    parser.add_argument('--n_folds', type=int, default=5)
    parser.add_argument('--n_inter_min', type=int, default=100)
    parser.add_argument('--n_inter_max', type=int, default=1000)

    # parser.add_argument('--n_obs_max', type=list, default=10000)
    # parser.add_argument('--n_obs_min', type=list, default=1000)

    parser.add_argument('--n_obs', type=int, default=10000)

    # ihdp hidden conf strength
    parser.add_argument('--conf_strength', type=float, default=0.5)

    # parser.add_argument('--output_folder', type=str, default=None) # keep it as None for local exp

    # Model settings
    # parser.add_argument('--methods', type=list, default=['TCP'])
    parser.add_argument('--methods', type=list, default=['naive', 'TCP', 'exact', 'inexact', 'weighted CP'])

    parser.add_argument('--base_learner', type=str, default="GBM")
    parser.add_argument('--density_ratio_model', type=str, default="MLP")
    parser.add_argument('--n_estimators', type=int, default=50)
    parser.add_argument('--quantile_regression', type=bool, default=True, 
                        help="True for quantile regression, False for normal regression")
    
    # TCP
    parser.add_argument('--n_Y_bins', type=int, default=10)

    args = parser.parse_args()

    return args

def main(args):
    # Get the current time
    current_time = datetime.now()
    cur_time = current_time.strftime("%m-%d")
    # Generating a 4 digit random integer to avoid fn collision
    random_number = random.randint(1000, 9999)

    args = utils.preprocess(args)
    np.random.seed(args.seed)

    n_observation = args.n_obs
    # n_intervention_list = np.arange(100, 1000, 100)
    n_intervention_list =  np.arange(args.n_inter_min, args.n_inter_max, 100)

    d = 10
    alpha = 0.1
    test_frac = 0.001 # n_observation * (1. - test_frac) is the real n_observation
    n_folds = 3
    err_scale = 0.1

    # df_train, df_test = generate_lilei_hua_data()
    # _ = weighted_conformal_prediction([df_train, df_test], 
    #                                   metalearner="DR", 
    #                                   quantile_regression=True, 
    #                                   alpha=0.1, 
    #                                   test_frac=0.1)
    # df_o = [df_train, df_test]

    for n_intervention in n_intervention_list:
        # n_intervention = args.n_intervention
            
        if args.dataset == 'synthetic':
            df_o, df_i = generate_data(n_observation=n_observation,    
                                n_intervention=n_intervention,
                                d=d, 
                                gamma=args.conf_strength, 
                                alpha=alpha,
                                confounding=True)
            
        elif args.dataset == 'cevae':
            df_o, df_i = generate_cevae_data(n_observation, n_intervention, err_scale = err_scale)

        elif args.dataset == 'ihdp':
            # as ihdp is a small dataset w. 740+ samples
            # we only allow the n_intervention to be no larger than 500
            if n_intervention > 500:
                print("n_intervention must be no larger than 500 for ihdp dataset")
                return
            
            df_o, df_i = IHDP_w_HC(n_intervention, args.seed, d=24,
                hidden_confounding=True, beta_u=args.beta_u, root="/mnt/bn/confrank2/causal_TCP/data/IHDP")


        else:
            raise ValueError('select a dataset from [synthetic]')
            
        # naive baseline
        if 'naive' in args.methods:
            res = run_conformal(
                                df_o,
                                df_i,
                                quantile_regression=True,
                                n_folds=n_folds,
                                alpha=alpha,
                                test_frac=test_frac,
                                target="counterfactual",
                                method = 'naive')
            
            utils.save_results(args, res, n_intervention, n_observation, cur_time, random_number)

        if 'inexact' in args.methods:
            res = run_conformal(
                                df_o,
                                df_i,
                                quantile_regression=True,
                                n_folds=n_folds,
                                alpha=alpha,
                                test_frac=test_frac,
                                target="counterfactual",
                                method = 'inexact')
            
            utils.save_results(args, res, n_intervention, n_observation, cur_time, random_number)

        if 'exact' in args.methods:

            res = run_conformal(
                                df_o,
                                df_i,
                                quantile_regression=True,
                                n_folds=n_folds,
                                alpha=alpha,
                                test_frac=test_frac,
                                target="counterfactual",
                                method = 'exact')
            
            utils.save_results(args, res, n_intervention, n_observation, cur_time, random_number)

        if 'weighted CP' in args.methods:
            res = weighted_conformal_prediction(df_o, 
                                            quantile_regression=True, 
                                            alpha=alpha, 
                                            test_frac=test_frac,
                                            target="counterfactual",
                                            method='weighted CP')
            
            utils.save_results(args, res, n_intervention, n_observation, cur_time, random_number)

        if 'TCP' in args.methods:
            res = run_conformal(
                                df_o,
                                df_i,
                                quantile_regression=args.quantile_regression, # QR not implemented yet
                                n_folds=n_folds,
                                alpha=alpha,
                                test_frac=test_frac,
                                target="counterfactual",
                                method = 'TCP',
                                density_ratio_model=args.density_ratio_model,
                                base_learner=args.base_learner,
                                n_estimators=args.n_estimators)
            
            utils.save_results(args, res, n_intervention, n_observation, cur_time, random_number)

            # coverage, average_interval_width, PEHE, conformity_scores = conformal_metalearner(df_o, 
            #                                                                                 metalearner="DR", 
            #                                                                                 quantile_regression=True, 
            #                                                                                 alpha=0.1, 
            #                                                                                 test_frac=0.1)

    pause = True
    return


if __name__ == '__main__':
    args = get_config()
    main(args)