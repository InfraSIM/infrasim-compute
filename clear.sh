#!/usr/bin/env sh

ip netns delete node-0
ip netns delete node-1
ip netns delete node-2
ip netns delete node-3

ovs-vsctl del-br br-ex
ovs-vsctl del-br br-int

#sleep 1
ip link delete veth0
ip link delete veth1

ip link delete veth2
ip link delete veth3
