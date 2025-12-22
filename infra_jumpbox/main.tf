provider "aws" {
  region = "us-east-1"
}

# 1. IAM Role for the Jumpbox (Must be Admin to deploy other things)
resource "aws_iam_role" "jumpbox_role" {
  name = "LexGuard_Jumpbox_Role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "jumpbox_admin" {
  role       = aws_iam_role.jumpbox_role.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

resource "aws_iam_instance_profile" "jumpbox_profile" {
  name = "LexGuard_Jumpbox_Profile"
  role = aws_iam_role.jumpbox_role.name
}

# 2. Key Pair for SSHing into Jumpbox
resource "tls_private_key" "jumpbox_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "jumpbox_key" {
  key_name   = "lexguard_jumpbox_key"
  public_key = tls_private_key.jumpbox_key.public_key_openssh
}

resource "local_file" "jumpbox_pem" {
  content  = tls_private_key.jumpbox_key.private_key_pem
  filename = "jumpbox_key.pem"
  file_permission = "0400"
}

# 3. Security Group (Allow SSH)
resource "aws_security_group" "jumpbox_sg" {
  name        = "LexGuard_Jumpbox_SG"
  description = "Allow SSH to Jumpbox"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# 4. The Jumpbox Instance
resource "aws_instance" "jumpbox" {
  ami           = "ami-04b70fa74e45c3917" # Ubuntu 24.04 LTS (US-East-1)
  instance_type = "t3.small"
  key_name      = aws_key_pair.jumpbox_key.key_name
  iam_instance_profile = aws_iam_instance_profile.jumpbox_profile.name
  vpc_security_group_ids = [aws_security_group.jumpbox_sg.id]

  # Cloud-Init Script
  user_data = <<-EOF
              #!/bin/bash
              echo ">>> Starting Setup..."
              
              # 1. Install Tools
              apt-get update -y
              apt-get install -y unzip zip jq curl
              
              # Install AWS CLI v2
              curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
              unzip awscliv2.zip
              ./aws/install
              
              # Install Terraform
              wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
              echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/hashicorp.list
              apt-get update && apt-get install -y terraform

              # 2. Download LexGuard Code
              mkdir -p /home/ubuntu/LexGuard
              aws s3 cp s3://lexguard-artifact-interview-stg/lexguard_demo.zip /home/ubuntu/lexguard_demo.zip
              unzip -o /home/ubuntu/lexguard_demo.zip -d /home/ubuntu/temp_unzip
              # Verify if it has nested folder
              if [ -d "/home/ubuntu/temp_unzip/LexGuard" ]; then
                  mv /home/ubuntu/temp_unzip/LexGuard/* /home/ubuntu/LexGuard/
              else
                  mv /home/ubuntu/temp_unzip/* /home/ubuntu/LexGuard/
              fi
              rm -rf /home/ubuntu/temp_unzip

              # 3. Setup Permissions
              chown -R ubuntu:ubuntu /home/ubuntu/LexGuard
              chmod +x /home/ubuntu/LexGuard/deploy_ami.sh
              
              # 4. Signal Complete
              echo ">>> Setup Complete" > /var/log/setup_complete
              EOF

  tags = {
    Name = "LexGuard_Jumpbox_Workstation"
  }
}

output "jumpbox_ip" {
  value = aws_instance.jumpbox.public_ip
}

output "ssh_command" {
  value = "ssh -i jumpbox_key.pem ubuntu@${aws_instance.jumpbox.public_ip}"
}
