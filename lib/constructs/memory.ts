import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

interface ChatMemoryProps {
  retainData: boolean;
}

export class ChatMemory extends Construct {
  public readonly memoryTable : dynamodb.Table;

  constructor(scope: Construct, id: string, props: ChatMemoryProps) {
    super(scope, id);

    const memoryTable = new dynamodb.Table(this, 'MemoryTable', {
      partitionKey: {
        name: 'SessionId',
        type: dynamodb.AttributeType.STRING,
      },
      removalPolicy: props.retainData ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });

    this.memoryTable = memoryTable;
  }
}
