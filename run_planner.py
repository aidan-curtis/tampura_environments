from __future__ import annotations

import argparse
import logging
import os
import pickle
import random
import time

import numpy as np
import tampura
from tampura.config import config as tconfig

import tampura_environments


def create_parser():

    save_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "runs",
        "run_{}".format(str(time.time())),
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="The config file to load from")
    parser.add_argument("--task", type=str),
    parser.add_argument("--planner", type=str)
    parser.add_argument(
        "--global-seed",
        help="The global rng seed set once before planner execution",
        type=int,
    )
    parser.add_argument(
        "--vis",
        help="A flag enabling visualization of the pybullet execution",
        type=bool,
    )
    parser.add_argument(
        "--vis-graph",
        help="A flag enabling visualization of the learned transition graphs",
        type=bool,
    )
    parser.add_argument(
        "--print-options",
        help="Specifies what to print at each step of execution",
    )

    parser.add_argument("--save-dir", help="File to load from", default=save_dir)
    parser.add_argument("--max-steps", help="Maximum number of steps allowed", type=int)

    parser.add_argument(
        "--batch-size",
        help="Number of samples from effect model before replanning.",
        type=int,
    )
    parser.add_argument(
        "--num-skeletons",
        help="Number of symbolic skeletons to extract from symk",
        type=int,
    )
    parser.add_argument(
        "--flat-sample",
        help="Sample all continuous controller input params once at the beginning.",
        type=bool,
    )
    parser.add_argument("--flat-width", help="Width when flat sampling", type=int)
    parser.add_argument(
        "--pwa", help="Progressive widening alpha parameter", type=float
    )
    parser.add_argument("--pwk", help="Progressive widening k parameter", type=float)
    parser.add_argument("--gamma", help="POMDP decay parameter", type=float)
    parser.add_argument(
        "--envelope-threshold",
        help="Number of samples from effect model before replanning.",
        type=float,
    )
    parser.add_argument(
        "--num-samples", help="Maximum number of steps allowed", type=int
    )
    parser.add_argument(
        "--learning-strategy",
        choices=["bayes_optimistic", "monte_carlo", "mdp_guided", "none"],
    )
    parser.add_argument(
        "--decision-strategy", choices=["prob", "wao", "ao", "mlo", "none"]
    )

    parser.add_argument("--symk-selection", choices=["unordered", "top_k"])

    parser.add_argument("--symk-direction", choices=["fw", "bw", "bd"])
    parser.add_argument("--symk-simple", type=bool)
    parser.add_argument("--from-scratch", type=bool)

    parser.add_argument(
        "--load",
        help="Location of the save folder to load from when visualizing",
    )
    return parser


if __name__ == "__main__":
    parser = create_parser()
    arg_dict = {k: v for k, v in vars(parser.parse_args()).items() if v is not None}
    config = tconfig.load_config(config_file=arg_dict["config"], arg_dict=arg_dict)

    execution_data = None
    if "load" in config and config["load"] is not None:
        pkl_files = [
            os.path.join(root, file)
            for root, _, files in os.walk(config["load"])
            for file in files
            if file.endswith(".pkl")
        ]
        assert len(pkl_files) == 1
        with open(pkl_files[0], "rb") as f:
            execution_data = pickle.load(f)
        new_config = execution_data.config
        new_config["planner"] = config["planner"]
        new_config["vis"] = config["vis"]
        new_config["save_dir"] = "{}_replay_{}".format(
            config["save_dir"], str(time.time())
        )
        config = new_config

    random.seed(config["global_seed"])
    np.random.seed(config["global_seed"])

    tconfig.setup_logger(config["save_dir"], log_level=logging.INFO)

    env = tconfig.get_env(config["task"])(config=config)
    b0, store = env.initialize()
    if execution_data is not None:
        store = execution_data.stores[-1]

    policy = tconfig.get_planner(config["planner"])(
        config, env.problem_spec, execution_data=execution_data
    )
    (_, _) = policy.rollout(env, b0, store)
