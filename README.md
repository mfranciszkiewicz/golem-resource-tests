# golem-resource-tests

This utility sets up an exchange of resources between two peers, using an external tool (currently IPFS and Dat). Total time of downloads and time per download are measured.

## Installation
```
pip install -r requirements.txt
```

## Usage
TODO

## Default scenario

- server generates a file resource of given size,
- client uses the resource sharing tool to download the resource,
- client publishes 3 random resources of predefined size,
- server uses the tool to download the forementioned files from the client.

This scenario is repeated `n` times (`--tasks` argument). Downloads are performed in a sequence.


## NAT traversal

NAT traversal is not implemented. In order to enable connectivity between nodes, create the following node setup:

```
NAT    ---> PUBLIC IP --->    NAT
CLIENT        PROXY        SERVER
```
