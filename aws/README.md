# Déploiement AWS — Impayes AI (eu-north-1)

Déploiement « tout en ligne » : **une seule EC2 t2.micro** (Free Tier) sert la démo
**et** l'API **et** MLflow. Conçu pour la démo de soutenance, pas pour le scale.

## Hypothèses Free Tier

| Ressource | Choix | Coût |
|---|---|---|
| EC2 | t2.micro (1 vCPU / 1 Go), Amazon Linux 2023 | **0 $ (12 mois)** — 750 h/mois |
| Stockage | 30 Go EBS gp3 (Free Tier max) | **0 $** |
| EIP | 1 EIP **associée** (indispensable pour l'URL stable) | **0 $** tant qu'elle est associée |
| Trafic | ≤ 1 Go/mois sortant | **0 $** |

⚠️ **Pièges Free Tier** : un Elastic IP **non associé** est facturé ~0,005 $/h (~3,5 $/mois) ;
après 12 mois votre compte basculera à ~7,5 $/mois minimum. Quand il ne sert plus :
**déconnecter + libérer l'EIP**, **terminer l'instance** (même arrêtée elle consomme des Go EBS).

## Étapes (console eu-north-1)

1. **EC2 → Security Groups → Create**
   - Nom : `impayes-demo` — VPC : défaut
   - Inbound : `22` (SSH, source = votre IP) · `80` (HTTP, 0.0.0.0/0) · `5000` (MLflow UI, 0.0.0.0/0)
   - Outbound : `0.0.0.0/0`
2. **EC2 → Launch instance**
   - Nom : `impayes-ai-demo` · Amazon Linux 2023 AMI · **t2.micro** (Free Tier eligible)
   - Key pair : **Proceed without a key pair** (tout passe par userdata, aucun SSH requis)
   - Network : SG `impayes-demo` · Storage : 30 GB `gp3`
   - **Advanced → Detailed CloudWatch → désactivé** (évite des frais)
   - **Advanced → User data** : coller `aws/userdata.sh`
3. **Elastic IP → Allocate → Associate** sur l'instance
4. Attendre 4–6 min (bootstrap systemd : `tail /var/log/impayes-bootstrap.log`)
5. Vérifier : `http://<EIP>/` → démo · `http://<EIP>/api/health` → `{"status":"ok","model_version":1}` · `http://<EIP>:5000` → MLflow UI

## Résiliation

EC2 → Terminate instance → **Elastic IP → Disassociate → Release** → Delete SG `impayes-demo`.
Le compte revient à 0 $.
