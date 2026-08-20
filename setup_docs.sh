#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup_docs.sh
#
# Builds a local docs/ folder for cloud, virtualization, networking, and
# infrastructure vendors and downloads the official PDF guides that vendors
# actually publish as single files.
#
# Vendor folders: aws, azure, gcp, cisco, nutanix, vmware, arista, hp, lenovo,
# and dell.
#
# IMPORTANT — run this on YOUR machine, not in a sandboxed/restricted shell.
# It needs outbound HTTPS to docs.aws.amazon.com and techdocs.broadcom.com.
#
# Most networking and infrastructure vendors publish web documentation or
# portal-hosted manuals rather than stable public PDF bundles. For those
# vendors this script writes LINKS.md with official entry points instead of
# guessing download URLs that will break when a release changes.
# ---------------------------------------------------------------------------
set -uo pipefail

BASE="docs"
mkdir -p "$BASE"/{aws,gcp,azure,cisco,nutanix,vmware,arista,hp,lenovo,dell,other}

download() {
  local url="$1" out="$2"
  echo "-> $out"
  if curl -fsSL "$url" -o "$out"; then
    echo "   OK ($(du -h "$out" | cut -f1))"
  else
    echo "   FAILED — AWS/Broadcom occasionally rename these paths on new releases."
    echo "   Grab it manually from the HTML page's 'PDF' button instead: $url"
    rm -f "$out"
  fi
}

echo "== AWS user guides =="
download "https://docs.aws.amazon.com/pdfs/AWSEC2/latest/UserGuide/ec2-ug.pdf"                    "$BASE/aws/ec2-user-guide.pdf"
download "https://docs.aws.amazon.com/pdfs/vpc/latest/userguide/vpc-ug.pdf"                        "$BASE/aws/vpc-user-guide.pdf"
download "https://docs.aws.amazon.com/pdfs/IAM/latest/UserGuide/iam-ug.pdf"                        "$BASE/aws/iam-user-guide.pdf"
download "https://docs.aws.amazon.com/pdfs/eks/latest/userguide/eks-ug.pdf"                        "$BASE/aws/eks-user-guide.pdf"
download "https://docs.aws.amazon.com/pdfs/AmazonS3/latest/userguide/s3-userguide.pdf"             "$BASE/aws/s3-user-guide.pdf"
download "https://docs.aws.amazon.com/pdfs/AmazonCloudWatch/latest/monitoring/acw-ug.pdf"          "$BASE/aws/cloudwatch-user-guide.pdf"

echo ""
echo "== VMware vSphere (now hosted on Broadcom TechDocs) =="
download "https://techdocs.broadcom.com/content/dam/broadcom/techdocs/us/en/pdf/vmware/vsphere/vsphere/vmware-vsphere-8-0.pdf" "$BASE/vmware/vsphere-8.0.pdf"

echo ""
echo "== GCP, Azure, Nutanix, Cisco, Arista, HP, Lenovo, Dell =="
echo "Writing curated official network and infrastructure documentation links."

cat > "$BASE/gcp/LINKS.md" <<'EOF'
# GCP reference docs (no official PDF export exists)
- Compute Engine: https://cloud.google.com/compute/docs
- GKE (Kubernetes):  https://cloud.google.com/kubernetes-engine/docs
- IAM:               https://cloud.google.com/iam/docs
- VPC:               https://cloud.google.com/vpc/docs
- Terraform on GCP:  https://cloud.google.com/docs/terraform
EOF

cat > "$BASE/azure/LINKS.md" <<'EOF'
# Azure reference docs (Microsoft Learn has no official PDF export)
- Azure fundamentals:        https://learn.microsoft.com/en-us/azure/?product=popular
- Virtual Machines:          https://learn.microsoft.com/en-us/azure/virtual-machines/
- AKS (Kubernetes):          https://learn.microsoft.com/en-us/azure/aks/
- Azure RBAC / IAM:          https://learn.microsoft.com/en-us/azure/role-based-access-control/
- Bicep / ARM templates (IaC): https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/
EOF

cat > "$BASE/nutanix/LINKS.md" <<'EOF'
# Nutanix reference docs
# Official portal PDFs require a (free) Nutanix account login, so they can't
# be curled headlessly — log in and download manually from these pages.
- Support Portal docs list:      https://portal.nutanix.com/page/documents/list
- Prism Central Guide:           search "Prism Central Guide" from the portal above

# Unofficial but excellent and freely downloadable (per-section PDF button),
# written by Nutanix's own field/engineering team — great for AOS/AHV
# architecture concepts without needing a login:
- Nutanix Bible:                 https://www.nutanixbible.com/
EOF

cat > "$BASE/cisco/LINKS.md" <<'EOF'
# Cisco network and infrastructure reference docs
- Cisco product documentation: https://www.cisco.com/c/en/us/support/index.html
- Cisco IOS XE: https://www.cisco.com/c/en/us/support/ios-nx-os-software/ios-xe/tsd-products-support-series-home.html
- Cisco NX-OS: https://www.cisco.com/c/en/us/support/switches/nexus-9000-series-switches/tsd-products-support-series-home.html
- Cisco Catalyst 9000: https://www.cisco.com/c/en/us/support/switches/catalyst-9000-series-switches/tsd-products-support-series-home.html
- Cisco data center networking: https://www.cisco.com/c/en/us/solutions/data-center-virtualization/index.html
- Cisco security: https://www.cisco.com/c/en/us/products/security/index.html
EOF

cat > "$BASE/arista/LINKS.md" <<'EOF'
# Arista network and infrastructure reference docs
- Arista documentation portal: https://www.arista.com/en/support/product-documentation
- EOS user manuals: https://www.arista.com/en/support/toi/eos-user-manuals
- EOS configuration guides: https://www.arista.com/en/support/toi/eos-configuration-guides
- CloudVision: https://www.arista.com/en/products/cloudvision
- Data center switching: https://www.arista.com/en/solutions/data-center
EOF

cat > "$BASE/hp/LINKS.md" <<'EOF'
# HPE and Aruba network and infrastructure reference docs
- HPE support documentation: https://support.hpe.com/connect/s/
- HPE networking: https://www.hpe.com/us/en/networking.html
- Aruba Networking documentation: https://www.arubanetworks.com/techdocs/
- ArubaOS-CX documentation: https://www.arubanetworks.com/techdocs/AOS-CX/10.13/HTML/5200-7324/
- HPE ProLiant servers: https://support.hpe.com/connect/s/product?language=en_US&kmpmoid=1010006816
- HPE storage: https://support.hpe.com/connect/s/product?language=en_US&kmpmoid=1009939596
EOF

cat > "$BASE/lenovo/LINKS.md" <<'EOF'
# Lenovo infrastructure and networking reference docs
- Lenovo enterprise support: https://datacentersupport.lenovo.com/
- ThinkSystem product documentation: https://pubs.lenovo.com/
- ThinkSystem servers: https://pubs.lenovo.com/thinksystem/
- ThinkSystem storage: https://pubs.lenovo.com/storage/
- Lenovo XClarity Administrator: https://pubs.lenovo.com/lxca/
- Lenovo networking products: https://datacentersupport.lenovo.com/products/servers/thinksystem
EOF

cat > "$BASE/dell/LINKS.md" <<'EOF'
# Dell infrastructure and networking reference docs
- Dell Technologies support: https://www.dell.com/support/home/
- Dell PowerSwitch documentation: https://www.dell.com/support/kbdoc/en-us/000019891/dell-emc-networking-documentation
- Dell OS10 documentation: https://www.dell.com/support/kbdoc/en-us/000103964/dell-emc-networking-os10-information-hub
- Dell PowerEdge servers: https://www.dell.com/support/kbdoc/en-us/000131456/poweredge-servers-documentation
- Dell PowerStore documentation: https://www.dell.com/support/kbdoc/en-us/000131504/powerstore-documentation
- Dell OpenManage Enterprise: https://www.dell.com/support/kbdoc/en-us/000175879/dell-openmanage-enterprise
EOF

echo ""
echo "Done. Structure:"
find "$BASE" -maxdepth 2 -type f | sort
