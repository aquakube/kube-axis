import kopf

from utilities.axis import is_valid_axis_serial_number

def mutate(spec, name, namespace, patch, **kwargs):
    kopf.label(
        objs=[patch],
        labels={
            'app.kubernetes.io/name': name,
            'app.kubernetes.io/instance': f"{namespace}.{name}",
            'app.kubernetes.io/version': f"{spec['workflow']['version']}",
            'app.kubernetes.io/component': 'axis',
            'app.kubernetes.io/part-of': 'aquakube',
            'app.kubernetes.io/managed-by': 'axis-operator'
        },
    )


def validate(body, spec, **kwargs):
    """
    
    """
    # enforcing provision strategy validation
    provision_strategy = spec['workflow']['provision_strategy']
    if provision_strategy == "resolve_mac_address":
        mac_address = spec['network'].get('mac_address')
        subnet = spec['network'].get('subnet')

        if mac_address is None or subnet is None:
            raise kopf.AdmissionError("Must set mac_address and subnet if using 'resolve_mac_address' strategy")
        
        if not is_valid_axis_serial_number(serial_number=mac_address):
            raise kopf.AdmissionError(
                """
                Invalid mac_address.
                Serial numbers for Axis network video, print and document servers generally start with either 00408c or accc8e followed by another 6 hexadecimal characters.
                The serial number is identical to the product's hardware address (MAC address) and can be written in the format 00408c1a2b3c, accc8e1a2b3c, 00:40:8c:1a:2b:3c​ or acc:cc:8e:1a:2b:3c.
                """
            )

    elif provision_strategy == "dhcp_ip_address":
        dhcp_ip_address = spec['network'].get('dhcp_ip_address')
        subnet = spec['network'].get('subnet')
        
        if dhcp_ip_address is None or subnet is None:
            raise kopf.AdmissionError("Must set dhcp_ip_address and subnet if using 'dhcp_ip_address' strategy")

    # enforce network mode validation
    network_mode = spec['network']['mode']
    if network_mode == 'static':
        if spec['network'].get('static_ip_address') is None:
            raise kopf.AdmissionError("Must set static_ip_address if using 'static' network mode")
        if spec['network'].get('router_ip_address') is None:
            raise kopf.AdmissionError("Must set router_ip_address if using 'static' network mode")
    elif network_mode == 'dhcp':
        mac_address = spec['network'].get('mac_address')
        subnet = spec['network'].get('subnet')

        if mac_address is None or subnet is None:
            raise kopf.AdmissionError("Must set mac_address and subnet if using DHCP mode, this is so the operator can use resolve the IP address assigned automatically via DHCP")

