import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

interface CacheProps {
  retainData: boolean;
}

export class Cache extends Construct {
  public readonly tokenTable: dynamodb.Table;

  constructor(scope: Construct, id: string, props: CacheProps) {
    super(scope, id);

    const tokenCache = new dynamodb.Table(this, 'TokenCache', {
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      partitionKey: {
        name: 'TokenHash',
        type: dynamodb.AttributeType.STRING,
      },
      removalPolicy: props.retainData ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
      timeToLiveAttribute: 'ExpirationEpoch',
    });

    this.tokenTable = tokenCache;
  }
}
