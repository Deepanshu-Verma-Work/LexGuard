#!/bin/bash
echo "Packaging LexGuard for Interview Laptop..."

# 1. create staging area
rm -rf interview_kit
mkdir -p interview_kit/project
mkdir -p interview_kit/keys

# 2. Copy Code (Excluding heavy/git items)
rsync -av --progress . interview_kit/project \
    --exclude node_modules \
    --exclude .git \
    --exclude .terraform \
    --exclude .DS_Store \
    --exclude dist \
    --exclude interview_kit

# 3. Copy AWS Keys (WARNING: SENSITIVE - For Personal Transfer Only)
# Assuming keys are in infra/ or ~/.aws
# We'll copy the PEM key which is in infra/
cp infra/casechat_demo_key.pem interview_kit/keys/

# 4. Create Quick Setup Script for Laptop 2
cat <<EOF > interview_kit/setup_laptop2.sh
#!/bin/bash
echo ">>> Setting up LexGuard Interview Environment..."

# Check Homebrew
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install Terraform & AWS CLI
echo ">>> Installing Terraform & AWS CLI..."
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
brew install awscli

# Setup AWS Credentials (Interactive)
echo ">>> Configure AWS CLI (Enter your Access Keys from Laptop 1 if asked)"
aws configure

echo ">>> Setup Complete!"
echo "You can now run: cd project && ./deploy_ami.sh"
EOF

chmod +x interview_kit/setup_laptop2.sh

# 5. Zip it up
zip -r interview_kit.zip interview_kit
echo "DONE. Transfer 'interview_kit.zip' to Laptop 2."
