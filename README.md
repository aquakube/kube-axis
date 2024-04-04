# KUBE-AXIS

This repository manages the automated workflows for provisioning AXIS cameras.  These are cameras that are deployed on barges or other facilities like hatcheries for remote monitoring of the farm and security footage recording.

The basic steps in the provisioning process are as follows:
* Plug the AXIS camera into a DHCP network that your provisioning cluster has access too (Retrieve the IP address of the AXIS camera or use the devices MAC address for discovery)
* Create an AXIS custom resource in the Kubernetes cluster
* Check slack or google chat for the report of the provisioned AXIS camera

## Operator

The AXIS operator will deploy an argo workflow that manages the camera settings whenever an AXIS custom resource is created or updated.

## Workflow

The argo workflow manages discovering the camera on the network either by MAC or IP address.
Once discovered the camera is provisioned and then verified.
The results of the workflow are then sent out via google chat and slack.


```
rtsp://10.0.9.164/axis-media/media.amp?resolution=720x720&FPS=15&h264profile=high&videobitratemode=vbr&videocodec=h264&camera=1
```