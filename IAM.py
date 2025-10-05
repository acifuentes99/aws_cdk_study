import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as iam from 'aws-cdk-lib/aws-iam';

export class MyIamStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // 1. IAM Role for an EC2 Instance ⚙️
    // This role is intended to be attached to an EC2 instance.
    // The principal is the EC2 service itself.
    const ec2Role = new iam.Role(this, 'MyEC2Role', {
      // The entity that can assume this role. For EC2, it's the EC2 service.
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      roleName: 'WebAppInstanceRole',
      description: 'This role is assumed by an EC2 instance for application needs.',
      // Attach a managed policy from AWS for S3 read access.
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonS3ReadOnlyAccess'),
      ],
    });

    // 2. IAM Role for a User to Assume 🧑‍💻
    // This role is intended for an IAM user to switch to for elevated or different permissions.
    // The principal is an AWS account, allowing any user/role within it (with permissions) to assume this role.
    const userAssumableRole = new iam.Role(this, 'MyUserAssumableRole', {
      // The entity that can assume this role. Here, we allow principals in the same AWS account.
      assumedBy: new iam.AccountPrincipal(cdk.Aws.ACCOUNT_ID),
      roleName: 'DeveloperReadOnlyRole',
      description: 'This role can be assumed by developers for read-only access.',
    });

    // Add a custom inline policy to the user-assumable role.
    // This grants specific, fine-grained permissions.
    userAssumableRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'dynamodb:GetItem',
        'dynamodb:Scan',
        'dynamodb:Query',
        'dynamodb:ListTables',
      ],
      // For production, always scope this down to specific table ARNs!
      resources: ['*'],
    }));

    // Output the ARNs of the created roles for easy reference
    new cdk.CfnOutput(this, 'EC2RoleArn', {
      value: ec2Role.roleArn,
      description: 'ARN of the IAM role for the EC2 instance',
    });

    new cdk.CfnOutput(this, 'UserAssumableRoleArn', {
      value: userAssumableRole.roleArn,
      description: 'ARN of the IAM role for users to assume',
    });
  }
}
