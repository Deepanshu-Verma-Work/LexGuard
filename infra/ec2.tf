# -----------------------------------------------------------------------------
# EC2 "Demo Box" Resources
# -----------------------------------------------------------------------------

# 1. SSH Key Pair (Auto-generated for Demo)
resource "tls_private_key" "demo_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "demo_key" {
  key_name   = "casechat_demo_key"
  public_key = tls_private_key.demo_key.public_key_openssh
}

resource "local_file" "private_key" {
  content  = tls_private_key.demo_key.private_key_pem
  filename = "${path.module}/casechat_demo_key.pem"
  file_permission = "0400"
}

# 2. Security Group
resource "aws_security_group" "demo_sg" {
  name        = "casechat-demo-sg"
  description = "Allow HTTP and SSH for Demo"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
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

# 3. EC2 Instance
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

resource "aws_instance" "demo_box" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.micro"
  
  key_name      = aws_key_pair.demo_key.key_name
  subnet_id     = aws_subnet.public[0].id # Must be in Public Subnet
  vpc_security_group_ids = [aws_security_group.demo_sg.id]
  associate_public_ip_address = true

  # IAM Role for deployment permissions (if we want the box to run terraform)
  # For now, we just host the frontend, but let's give it power.
  iam_instance_profile = aws_iam_instance_profile.demo_profile.name

  user_data = file("${path.module}/user_data.sh")

  tags = {
    Name = "CaseChat-Demo-Box"
  }
}

# 4. IAM Role for the Box (Deployment & S3 Access)
resource "aws_iam_role" "demo_role" {
  name = "casechat_demo_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy_attachment" "demo_admin" {
  role       = aws_iam_role.demo_role.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess" # Simplify for Demo
}

resource "aws_iam_instance_profile" "demo_profile" {
  name = "casechat_demo_profile"
  role = aws_iam_role.demo_role.name
}

# 5. Output
output "demo_ip" {
  value = aws_instance.demo_box.public_ip
}

output "ssh_command" {
  value = "ssh -i infra/casechat_demo_key.pem ubuntu@${aws_instance.demo_box.public_ip}"
}
