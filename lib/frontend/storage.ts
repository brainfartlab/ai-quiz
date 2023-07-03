import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';

export class StaticHosting extends Construct {
  public readonly bucket: s3.IBucket;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    const bucket = new s3.Bucket(this, 'StorageBucket', {
    });
  }
}
