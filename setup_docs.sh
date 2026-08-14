#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup_docs.sh
#
# Builds a local docs/ folder (aws, gcp, azure, vmware, nutanix) and downloads
# the official PDF guides that vendors actually publish as single files.
#
# IMPORTANT — run this on YOUR machine, not in a sandboxed/restricted shell.
# It needs outbound HTTPS to docs.aws.amazon.com and techdocs.broadcom.com.
#
# Only AWS and VMware ship official single-file PDFs for their docs. GCP and
# Azure publish web-only documentation (no official PDF export), and Nutanix's
# PDF exports live behind a portal.nutanix.com login. For those three, this
# script instead writes a LINKS.md with the right entry points — see
# DOCS_REFERENCE.md alongside this script for the full picture.
# ---------------------------------------------------------------------------
set -uo pipefail

BASE="docs"
mkdir -p "$BASE"/{aws,gcp,azure,vmware,nutanix}

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
echo "== GCP, Azure, Nutanix =="
echo "No reliable single-file official PDF for these — writing curated link lists instead."

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

echo ""
echo "Done. Structure:"
find "$BASE" -maxdepth 2 -type f | sort
