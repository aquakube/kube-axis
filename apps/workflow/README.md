# AXIS Workflow

This workflow will provision and configure AXIS cameras.

The steps to this workflow are as follows:
1. Device Discovery
2. Camera Provisioning
3. Verification
4. Notification

## Device Discovery

The first step in the workflow is device discovery.
This step will check the field `axis.spec.workflow.provision_strategy` to determine if the workflow should discover the camera through mac address or ip address.

## Camera Provisioning

Once the camera has been discovered, the camera is provisioned with the provided network and camera settings.

## Verification

Once the camera has been provisioned, the settings are verified on the camera.

## Notification

The results of the workflow are output to slack and google chat for review.

