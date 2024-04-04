# AXIS Operator

This operator will react to AXIS Custom Resources defined in the cluster.
On CRUD events the operator will respectivelly provsion or configure the AXIS device.


## Run

```
kopf run --namespace axis apps/operator/src/main.py
```