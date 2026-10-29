"""ROS 2 düğümlerinin duman testi: GERÇEK ROS yerine sahte rclpy modülleriyle, simülasyon üzerinde.
Amaç: yazım/öznitelik hatalarını ve temel mantığı (komut -> hareket, bayat tarama -> dur) yakalamak.
Gerçek ROS davranışını (QoS, TF, zamanlayıcılar) DOĞRULAMAZ; o Pi'de denenmelidir."""
import importlib.util
import math
import pathlib
import sys
import time
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from arac.sim_world import World  # noqa: E402


class Msg:
    def __init__(self):
        object.__setattr__(self, "_d", {})

    def __getattr__(self, k):
        d = object.__getattribute__(self, "_d")
        if k not in d:
            d[k] = [0.0] * 36 if k == "covariance" else Msg()
        return d[k]

    def __setattr__(self, k, v):
        object.__getattribute__(self, "_d")[k] = v


def val(x):
    """Gerçek ROS mesajlarında atanmamış sayısal alan 0.0'dır; sahte Msg'de karşılığı budur."""
    return 0.0 if isinstance(x, Msg) else x


class FakeNode:
    def __init__(self, name):
        self.published, self.subs = [], {}

    def create_subscription(self, typ, topic, cb, qos):
        self.subs[topic] = cb

    def create_publisher(self, typ, topic, qos):
        node = self

        class Pub:
            def publish(self, msg):
                node.published.append((topic, msg))
        return Pub()

    def create_timer(self, period, cb):
        return cb

    def get_logger(self):
        return types.SimpleNamespace(info=lambda *a: None, error=lambda *a: None, warn=lambda *a: None)

    def get_clock(self):
        return types.SimpleNamespace(now=lambda: types.SimpleNamespace(to_msg=lambda: Msg()))

    def destroy_node(self):
        pass


def install_fakes():
    def mod(name, **attrs):
        m = types.ModuleType(name)
        m.__dict__.update(attrs)
        sys.modules[name] = m
        return m
    mod("rclpy", init=lambda *a, **k: None, spin=lambda n: None, ok=lambda: False, shutdown=lambda: None)
    mod("rclpy.node", Node=FakeNode)
    mod("rclpy.qos", qos_profile_sensor_data=object())
    mod("geometry_msgs")
    mod("geometry_msgs.msg", Twist=Msg, TransformStamped=Msg)
    mod("nav_msgs")
    mod("nav_msgs.msg", Odometry=Msg)
    mod("sensor_msgs")
    mod("sensor_msgs.msg", LaserScan=Msg)
    mod("tf2_ros", TransformBroadcaster=lambda node: types.SimpleNamespace(sendTransform=lambda t: None))


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "ros" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class RosSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_fakes()
        cls.drive_mod = load("drive_node")
        cls.wall_mod = load("wall_follow_node")

    def test_drive_node_moves_with_cmd(self):
        node = self.drive_mod.DriveNode(mock=True)
        cmd = Msg()
        cmd.linear.x, cmd.angular.z = 0.25, 0.0
        for _ in range(300):
            node.on_cmd(cmd)
            node.tick()
            time.sleep(0.001)
        self.assertGreater(node.drive.odom.x, 0.05)
        node.shutdown()

    def test_wall_follow_node_commands_and_stale_scan(self):
        node = self.wall_mod.WallFollowNode("right", 1.0, 2, countdown=0.0)
        world = World([(-1, -1.0, 12, -1.0), (-1, 4.0, 12, 4.0), (12, -1.0, 12, 4.0)])
        ranges, amin, inc = world.scan(0.0, -0.1, 0.0, n=720)
        scan = Msg()
        scan.ranges, scan.angle_min, scan.angle_increment = list(ranges), amin, inc
        scan.range_min, scan.range_max = 0.05, 12.0
        node.on_scan(scan)
        node.tick()
        topic, cmd = node.published[-1]
        self.assertGreater(val(cmd.linear.x), 0.0)                    # duvar var: ilerler
        node.scan_t -= 5.0                                       # tarama bayatladı
        node.tick()
        self.assertEqual(val(node.published[-1][1].linear.x), 0.0)    # LiDAR kopunca durur


if __name__ == "__main__":
    unittest.main()
