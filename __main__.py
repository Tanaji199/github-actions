import pulumi
import pulumi_aws as aws

# ----- CONFIG -----
ami = "ami-052064a798f08f0d3"  # your AMI ID
instance_type = "t2.micro"
key_name = "pulukey"            # your AWS key pair name
my_ip = "157.32.199.235/32"     # your public IP for SSH

# ----- VPC -----
vpc = aws.ec2.Vpc("dev-vpc",
    cidr_block="10.0.0.0/16",
    enable_dns_support=True,
    enable_dns_hostnames=True,
    tags={"Name": "dev-vpc"}
)

# ----- Internet Gateway -----
igw = aws.ec2.InternetGateway("dev-igw", vpc_id=vpc.id)

# ----- Public Subnet -----
public_subnet = aws.ec2.Subnet("public-subnet",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    map_public_ip_on_launch=True,
    tags={"Name": "public-subnet"}
)

# ----- Private Subnet -----
private_subnet = aws.ec2.Subnet("private-subnet",
    vpc_id=vpc.id,
    cidr_block="10.0.2.0/24",
    map_public_ip_on_launch=False,
    tags={"Name": "private-subnet"}
)

# ----- Public Route Table -----
public_rt = aws.ec2.RouteTable("public-rt",
    vpc_id=vpc.id,
    routes=[aws.ec2.RouteTableRouteArgs(
        cidr_block="0.0.0.0/0",
        gateway_id=igw.id
    )]
)
aws.ec2.RouteTableAssociation("public-rt-assoc",
    route_table_id=public_rt.id,
    subnet_id=public_subnet.id
)

# ----- NAT Gateway -----
eip = aws.ec2.Eip("nat-eip")
nat_gw = aws.ec2.NatGateway("nat-gw",
    allocation_id=eip.id,
    subnet_id=public_subnet.id,
    tags={"Name": "nat-gateway"}
)

# ----- Private Route Table -----
private_rt = aws.ec2.RouteTable("private-rt",
    vpc_id=vpc.id,
    routes=[aws.ec2.RouteTableRouteArgs(
        cidr_block="0.0.0.0/0",
        nat_gateway_id=nat_gw.id
    )]
)
aws.ec2.RouteTableAssociation("private-rt-assoc",
    route_table_id=private_rt.id,
    subnet_id=private_subnet.id
)

# ----- Security Groups -----
# Bastion SG: Allow SSH from your IP only
bastion_sg = aws.ec2.SecurityGroup("bastion-sg",
    vpc_id=vpc.id,
    description="Allow SSH from my IP",
    ingress=[aws.ec2.SecurityGroupIngressArgs(
        protocol="tcp",
        from_port=22,
        to_port=22,
        cidr_blocks=[my_ip]
    )],
    egress=[aws.ec2.SecurityGroupEgressArgs(
        protocol="-1",
        from_port=0,
        to_port=0,
        cidr_blocks=["0.0.0.0/0"]
    )],
    tags={"Name": "bastion-sg"}
)

# Private SG: Allow SSH from bastion only
private_sg = aws.ec2.SecurityGroup("private-sg",
    vpc_id=vpc.id,
    description="Allow SSH from bastion instance",
    ingress=[aws.ec2.SecurityGroupIngressArgs(
        protocol="tcp",
        from_port=22,
        to_port=22,
        security_groups=[bastion_sg.id]
    )],
    egress=[aws.ec2.SecurityGroupEgressArgs(
        protocol="-1",
        from_port=0,
        to_port=0,
        cidr_blocks=["0.0.0.0/0"]
    )],
    tags={"Name": "private-sg"}
)

# ----- Bastion EC2 -----
bastion = aws.ec2.Instance("bastion-instance",
    ami=ami,
    instance_type=instance_type,
    subnet_id=public_subnet.id,
    vpc_security_group_ids=[bastion_sg.id],
    associate_public_ip_address=True,
    key_name=key_name,
    tags={"Name": "bastion"}
)

# ----- Private EC2 -----
private_instance = aws.ec2.Instance("private-instance",
    ami=ami,
    instance_type=instance_type,
    subnet_id=private_subnet.id,
    vpc_security_group_ids=[private_sg.id],
    associate_public_ip_address=False,
    key_name=key_name,
    tags={"Name": "private-instance"}
)

# ----- Outputs -----
pulumi.export("vpc_id", vpc.id)
pulumi.export("bastion_public_ip", bastion.public_ip)
pulumi.export("private_instance_private_ip", private_instance.private_ip)
pulumi.export("nat_gateway_ip", eip.public_ip)
