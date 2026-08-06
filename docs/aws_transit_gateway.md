# AWS Transit Gateway and Core VPC Routing Specification

## Overlapping CIDR Blocks and Multi-Region Routing
When peering multiple Virtual Private Clouds (VPCs) via an AWS Transit Gateway (TGW), route table evaluation follows the Longest Prefix Match (LPM) rule. If static routes conflict with dynamic BGP propagation, static routes take precedence.

## MTU and Jumbo Frames
Transit Gateway supports an Maximum Transmission Unit (MTU) of 8500 bytes for traffic between VPCs attached to the TGW. Traffic over AWS Direct Connect gateway attachments supports up to 1500 bytes MTU. Packet sizes exceeding these limits without the DF (Don't Fragment) flag cleared will be dropped, resulting in silent packet loss across the VPN tunnel.

## Edge Association Rules
An AWS TGW route table can have multiple attachments associated with it, but an attachment can only be associated with a single TGW route table at a time. For security isolation (e.g., separating Dev and Prod traffic), a dual-route-table architecture must be deployed with route propagation disabled between the isolation zones.