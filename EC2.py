from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    CfnTag
)
from constructs import Construct

class Ec2PartitionEniStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Create a VPC
        vpc = ec2.Vpc(self, "VPC",
            max_azs=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                )
            ]
        )
        
        # We need a specific subnet to place the ENI and the instance.
        # We'll use the first public subnet from the VPC.
        subnet_selection = vpc.public_subnets[0]
        
        # 2. Create a Partition Placement Group
        partition_group = ec2.PlacementGroup(self, "PartitionPlacementGroup",
            strategy=ec2.PlacementGroupStrategy.PARTITION,
            partitions=3,  # Set the number of partitions (max 7 per AZ)
            removal_policy=cdk.RemovalPolicy.DESTROY # Adjust as needed
        )

        # 3. Define the EC2 Security Group
        security_group = ec2.SecurityGroup(self, "InstanceSG",
            vpc=vpc,
            description="Allow SSH",
            allow_all_outbound=True
        )

        security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(22),
            description="Allow SSH access"
        )

        # 4. Create the Secondary Elastic Network Interface (ENI)
        # Using CfnNetworkInterface to ensure it's explicitly created and attached.
        secondary_eni = ec2.CfnNetworkInterface(self, "SecondaryENI",
            subnet_id=subnet_selection.subnet_id,
            group_set=[security_group.security_group_id],
            description="Secondary ENI for EC2 Instance",
            # Optionally, assign a specific private IP:
            # private_ip_address="10.0.0.100" 
            tags=[
                CfnTag(key="Name", value="Secondary-ENI")
            ]
        )
        
        # Get an AMI for the EC2 Instance
        ami = ec2.MachineImage.latest_amazon_linux_2(
            edition=ec2.AmazonLinuxEdition.STANDARD,
            virtualization=ec2.AmiHardwareType.STANDARD,
            storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE
        )

        # 5. Create the EC2 Instance (using L1 CfnInstance for ENI attachment)
        # To attach a secondary ENI, you must use the L1 CfnInstance construct 
        # and configure the network interfaces property directly.
        ec2_instance = ec2.CfnInstance(self, "MyPartitionInstance",
            image_id=ami.get_image(self).image_id,
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.C5, ec2.InstanceSize.LARGE
            ).to_string(),
            key_name="your-key-pair-name", # Replace with your key pair name
            
            # --- Placement Group Configuration ---
            # Launch the instance into the partition placement group
            # PartitionNumber=0 is used here to select the first partition
            placement={
                "group_name": partition_group.placement_group_name,
                "partition_number": 0 
                # Note: Setting a PartitionNumber is optional; omitting it defaults to auto-distribution.
            },
            
            # --- Network Interface Configuration (Primary ENI & Secondary ENI) ---
            # When specifying networkInterfaces, you must define ALL interfaces, including the primary (deviceIndex 0).
            network_interfaces=[
                # Primary ENI (deviceIndex 0) - Must be explicitly defined now
                ec2.CfnInstance.NetworkInterfaceProperty(
                    device_index="0",
                    subnet_id=subnet_selection.subnet_id,
                    group_set=[security_group.security_group_id],
                    associate_public_ip_address=True # Primary ENI gets public IP
                ),
                # Secondary ENI (deviceIndex 1) - Attach the one we created
                ec2.CfnInstance.NetworkInterfaceProperty(
                    device_index="1",
                    network_interface_id=secondary_eni.ref
                )
            ]
        )
        
        # Output the instance details
        CfnOutput(self, "InstanceId", value=ec2_instance.ref)
        CfnOutput(self, "PlacementGroupName", value=partition_group.placement_group_name)

# --- Example App Setup (outside the stack definition) ---
from aws_cdk import App, Environment, CfnOutput
import os

app = App()

# Ensure you have the necessary environment context for deployment
Ec2PartitionEniStack(app, "PartitionEniStudyStack",
    env=Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"]
    )
)

app.synth()
