import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as sources from 'aws-cdk-lib/aws-lambda-event-sources';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as pythonLambda from '@aws-cdk/aws-lambda-python-alpha';
import * as secrets from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

interface GameFlowProps {
  commonLayer: lambda.ILayerVersion;
  gameTable: dynamodb.ITable;
  questionTable: dynamodb.ITable;
}

export class GameFlow extends Construct {
  public readonly gameFlowQueue: sqs.IQueue;

  constructor(scope: Construct, id: string, props: GameFlowProps) {
    super(scope, id);

    const openAIKey = new secrets.Secret(this, 'OpenAIKey');
    const designDuration = cdk.Duration.seconds(900);

    const gameDesignFunction = new pythonLambda.PythonFunction(this, 'GameDesignFunction', {
      entry: 'lib/backend/qagen',
      environment: {
        GAME_TABLE: props.gameTable.tableName,
        QUESTION_TABLE: props.questionTable.tableName,
        OPENAI_API_KEY_SECRET: openAIKey.secretName,
      },
      layers: [
        props.commonLayer,
      ],
      memorySize: 1024,
      runtime: lambda.Runtime.PYTHON_3_10,
      timeout: designDuration,
    });

    openAIKey.grantRead(gameDesignFunction);

    props.gameTable.grantReadWriteData(gameDesignFunction);
    props.questionTable.grantReadWriteData(gameDesignFunction);

    const gameQueue = new sqs.Queue(this, 'GameDesignQueue', {
      visibilityTimeout: designDuration,
    });

    gameDesignFunction.addEventSource(new sources.SqsEventSource(gameQueue, {
      batchSize: 1,
    }));

    this.gameFlowQueue = gameQueue;
  }
}
