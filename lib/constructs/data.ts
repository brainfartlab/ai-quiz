import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

interface DataProps {
  retainData: boolean;
}

export class Data extends Construct {
  public readonly gameTable: dynamodb.Table;
  public readonly questionTable: dynamodb.Table;

  constructor(scope: Construct, id: string, props: DataProps) {
    super(scope, id);

    const gameTable = new dynamodb.Table(this, 'GameTable', {
      partitionKey: {
        name: 'PlayerId',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'GameId',
        type: dynamodb.AttributeType.STRING,
      },
      removalPolicy: props.retainData ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });
    gameTable.addLocalSecondaryIndex({
      indexName: 'creation-time-index',
      sortKey: {
        name: 'CreationTime',
        type: dynamodb.AttributeType.NUMBER,
      },
      nonKeyAttributes: [
        'Keywords',
        'QuestionsLimit',
      ],
      projectionType: dynamodb.ProjectionType.INCLUDE,
    });

    const questionTable = new dynamodb.Table(this, 'QuestionTable', {
      partitionKey: {
        name: 'GameId',
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: 'QuestionId',
        type: dynamodb.AttributeType.NUMBER,
      },
      removalPolicy: props.retainData ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });

    this.gameTable = gameTable;
    this.questionTable = questionTable;
  }
}
