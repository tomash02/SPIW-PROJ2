#!/usr/bin/env python3

import subprocess
import time
import requests
import yaml
import os
import sys


KUBECONFIG = os.path.expanduser("~/.kube/config-cluster-06-19T19:14:03")
PROMETHEUS_ADDR = "192.168.1.201"
INTENT_FILE = "intent.yaml"
BASE_SCAN_TIME = 10
NAMESPACE = "open5gs"
POD_NAME_PATTERN = "open5gs-upf"
CONTAINER_NAME = "open5gs-upf"


def get_amf_session_count():
    query = 'amf_session{service="open5gs-amf-metrics",namespace="open5gs"}'
    resp = requests.get(f"http://{PROMETHEUS_ADDR}:9090/api/v1/query", params={'query': query})
    data = resp.json()
    try:
        return int(float(data["data"]["result"][0]["value"][1]))
    except (IndexError, KeyError, ValueError):
        return None

def load_intent_thresholds():
    with open(INTENT_FILE, "r") as f:
        intent = yaml.safe_load(f)
    return sorted(intent.get("thresholds", []), key=lambda x: x["sessions"], reverse=True)

def determine_cpu(session_count, thresholds):
    for entry in thresholds:
        if session_count >= entry["sessions"]:
            return entry["cpu"]
    return thresholds[-1]["cpu"]

def get_upf_pod_name():
    result = subprocess.run(
        ["kubectl", "--kubeconfig", KUBECONFIG, "get", "pods", "-n", NAMESPACE],
        stdout=subprocess.PIPE, text=True
    )
    for line in result.stdout.splitlines():
        if POD_NAME_PATTERN in line:
            return line.split()[0]
    return None

def patch_cpu(pod, cpu):
    patch = {
        "spec": {
            "containers": [
                {
                    "name": CONTAINER_NAME,
                    "resources": {
                        "limits": {
                            "cpu": cpu
                        }
                    }
                }
            ]
        }
    }
    subprocess.run([
        "kubectl", "--kubeconfig", KUBECONFIG, "patch", "pod", pod,
        "-n", NAMESPACE, "--subresource", "resize",
        "--patch", yaml.dump(patch)
    ])

def main():
    max_iter = int(sys.argv[1]) if len(sys.argv) > 1 else -1
    thresholds = load_intent_thresholds()
    iter_count = 0

    while True:
        iter_count += 1
        session_count = get_amf_session_count()
        if session_count is None:
            time.sleep(BASE_SCAN_TIME)
            continue

        cpu = determine_cpu(session_count, thresholds)
        pod = get_upf_pod_name()
        if not pod:
            sys.exit("UPF pod not found")

        print(f"[#{iter_count}] AMF sessions: {session_count} → CPU: {cpu} → pod: {pod}")
        patch_cpu(pod, cpu)

        if max_iter > 0 and iter_count >= max_iter:
            break
        time.sleep(BASE_SCAN_TIME)

if __name__ == "__main__":
    main()

