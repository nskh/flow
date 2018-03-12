"""
Example of a multi-lane network with human-driven vehicles.
"""
from flow.core.params import SumoParams, EnvParams, NetParams, InitialConfig, \
    InFlows
from flow.core.vehicles import Vehicles
from flow.core.traffic_lights import TrafficLights

from flow.scenarios.bridge_toll.gen import BBTollGenerator
from flow.scenarios.bridge_toll.scenario import BBTollScenario
from flow.controllers.lane_change_controllers import *
from flow.controllers.rlcontroller import RLController
from flow.controllers.routing_controllers import ContinuousRouter
from flow.core.params import SumoCarFollowingParams
from flow.core.params import SumoLaneChangeParams

from rllab.envs.gym_env import GymEnv
from rllab.envs.normalized_env import normalize
from rllab.misc.instrument import run_experiment_lite
from rllab.algos.trpo import TRPO
from rllab.baselines.linear_feature_baseline import LinearFeatureBaseline
from rllab.policies.gaussian_mlp_policy import GaussianMLPPolicy

SCALING = 1
NUM_LANES = 4*SCALING  # number of lanes in the widest highway
DISABLE_TB = True
DISABLE_RAMP_METER = True

logging.basicConfig(level=logging.INFO)

sumo_params = SumoParams(sim_step = 0.5, sumo_binary="sumo-gui")

vehicles = Vehicles()

vehicles.add(veh_id="rl",
             acceleration_controller=(RLController, {}),
             lane_change_controller=(SumoLaneChangeController, {}),
             routing_controller=(ContinuousRouter, {}),
             speed_mode=0b1111,
             lane_change_mode=1621,
             num_vehicles=4*SCALING,
             sumo_car_following_params=SumoCarFollowingParams(
                 minGap=2.5, tau=1.0),
             sumo_lc_params=SumoLaneChangeParams())
vehicles.add(veh_id="human",
             speed_mode=0b11111,
             lane_change_controller=(SumoLaneChangeController, {}),
             routing_controller=(ContinuousRouter, {}),
             lane_change_mode=512,
             sumo_car_following_params=SumoCarFollowingParams(
                 minGap=2.5, tau=1.0),
             num_vehicles=15*SCALING)
vehicles.add(veh_id="rl2",
             acceleration_controller=(RLController, {}),
             lane_change_controller=(SumoLaneChangeController, {}),
             routing_controller=(ContinuousRouter, {}),
             speed_mode=0b1111,
             lane_change_mode=1621,
             num_vehicles=4*SCALING,
             sumo_car_following_params=SumoCarFollowingParams(
                 minGap=2.5, tau=1.0),
             sumo_lc_params=SumoLaneChangeParams())
vehicles.add(veh_id="human2",
             speed_mode=0b11111,
             lane_change_mode=512,
             lane_change_controller=(SumoLaneChangeController, {}),
             routing_controller=(ContinuousRouter, {}),
             sumo_car_following_params=SumoCarFollowingParams(
                 minGap=2.5, tau=1.0),
             num_vehicles=15*SCALING)

additional_env_params = {"target_velocity": 40, "num_steps": 15000,
                         "disable_tb": True, "disable_ramp_metering": True}
env_params = EnvParams(additional_params=additional_env_params,
                       lane_change_duration=1)

# flow rate
flow_rate = 1500 * SCALING
# percentage of flow coming out of each lane
# flow_dist = np.random.dirichlet(np.ones(NUM_LANES), size=1)[0]
flow_dist = np.ones(NUM_LANES) / NUM_LANES

inflow = InFlows()
for i in range(NUM_LANES):
    lane_num = str(i)
    veh_per_hour = flow_rate * flow_dist[i]
    inflow.add(veh_type="human", edge="1", vehsPerHour=veh_per_hour,
               departLane=lane_num, departSpeed=10)

traffic_lights = TrafficLights()
if not DISABLE_TB:
    traffic_lights.add(node_id="2")
if not DISABLE_RAMP_METER:
    traffic_lights.add(node_id="3")

additional_net_params = {"scaling": SCALING}
net_params = NetParams(in_flows=inflow,
                       no_internal_links=False, additional_params=additional_net_params)

initial_config = InitialConfig(spacing="uniform", min_gap=5,
                               lanes_distribution=float("inf"),
                               edges_distribution=["2", "3", "4", "5"])

scenario = BBTollScenario(name="bay_bridge_toll",
                          generator_class=BBTollGenerator,
                          vehicles=vehicles,
                          net_params=net_params,
                          initial_config=initial_config,
                          traffic_lights=traffic_lights)


def run_task(*_):
    env_name = "BottleNeckEnv"
    pass_params = (env_name, sumo_params, vehicles, env_params,
                       net_params, initial_config, scenario)

    env = GymEnv(env_name, record_video=False, register_params=pass_params)
    horizon = env.horizon
    env = normalize(env)

    policy = GaussianMLPPolicy(
        env_spec=env.spec,
        hidden_sizes=(100, 50, 25)
    )

    baseline = LinearFeatureBaseline(env_spec=env.spec)

    algo = TRPO(
        env=env,
        policy=policy,
        baseline=baseline,
        batch_size=40000,
        max_path_length=horizon,
        # whole_paths=True,
        n_itr=400,
        discount=0.995,
        # step_size=0.01,
    )
    algo.train()

exp_tag = "BottleNeckVerySmall"  # experiment prefix
for seed in [1]:  # , 1, 5, 10, 73]:
    run_experiment_lite(
        run_task,
        # Number of parallel workers for sampling
        n_parallel=1,
        # Only keep the snapshot parameters for the last iteration
        snapshot_mode="all",
        # Specifies the seed for the experiment. If this is not provided, a
        # random seed will be used
        seed=seed,
        mode="local",
        exp_prefix=exp_tag,
        # python_command="/home/aboudy/anaconda2/envs/rllab-multiagent/bin/python3.5"
        # plot=True,
    )