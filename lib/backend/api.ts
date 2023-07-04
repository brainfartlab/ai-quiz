import * as cdk from 'aws-cdk-lib';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as sources from 'aws-cdk-lib/aws-lambda-event-sources';
import * as secrets from 'aws-cdk-lib/aws-secretsmanager';
import * as apigw2 from '@aws-cdk/aws-apigatewayv2-alpha';
import * as authorizers from '@aws-cdk/aws-apigatewayv2-authorizers-alpha';
import * as integrations from '@aws-cdk/aws-apigatewayv2-integrations-alpha';
import * as pythonLambda from '@aws-cdk/aws-lambda-python-alpha';
import { Construct } from 'constructs';

import { Auth0Settings, DomainSettings } from '../constants';

interface ApiProps {
  origin: string;
  gameTable: dynamodb.ITable;
  memoryTable: dynamodb.ITable;
  questionTable: dynamodb.ITable;
  tokenTable: dynamodb.ITable;
}

export class Api extends Construct {
  public readonly api: apigw2.IHttpApi;
  public readonly stage: apigw2.HttpStage;

  constructor(scope: Construct, id: string, props: ApiProps) {
    super(scope, id);

    const apiKey = new secrets.Secret(this, 'ApiKey');

    const handlerFunction = new pythonLambda.PythonFunction(this, 'HandlerFunction', {
      entry: 'lib/backend/app',
      environment: {
        GAME_TABLE: props.gameTable.tableName,
        SESSION_TABLE: props.memoryTable.tableName,
        QUESTION_TABLE: props.questionTable.tableName,
        TOKEN_TABLE: props.tokenTable.tableName,
        OPENAI_API_KEY_SECRET: apiKey.secretName,
      },
      memorySize: 256,
      runtime: lambda.Runtime.PYTHON_3_10,
      timeout: cdk.Duration.seconds(60),
    });

    apiKey.grantRead(handlerFunction);

    props.gameTable.grantReadWriteData(handlerFunction);
    props.memoryTable.grantReadWriteData(handlerFunction);
    props.questionTable.grantReadWriteData(handlerFunction);
    props.tokenTable.grantReadWriteData(handlerFunction);

    const quizIntegration = new integrations.HttpLambdaIntegration('Integration', handlerFunction);
    const authorizer = new authorizers.HttpJwtAuthorizer('JwtAuthorizer', Auth0Settings.ISSUER_URL, {
      identitySource: ['$request.header.Authorization'],
      jwtAudience: [Auth0Settings.AUDIENCE_URL],
    });
    const httpApi = new apigw2.HttpApi(this, 'HttpApi', {
      corsPreflight: {
        allowHeaders: [
          'authorization',
          'content-type',
          '*',
        ],
        allowMethods: [
          apigw2.CorsHttpMethod.GET,
          apigw2.CorsHttpMethod.POST,
          apigw2.CorsHttpMethod.PUT,
          apigw2.CorsHttpMethod.ANY,
        ],
        allowOrigins: [
          props.origin,
        ],
      },
      createDefaultStage: false,
      defaultAuthorizer: authorizer,
      // defaultIntegration: quizIntegration,
    });

    const stage = httpApi.addStage('default', {
      autoDeploy: true,
      throttle: {
        burstLimit: 20,
        rateLimit: 100,
      },
    });

    httpApi.addRoutes({
      integration: quizIntegration,
      methods: [
        apigw2.HttpMethod.GET,
        apigw2.HttpMethod.POST,
      ],
      path: '/games',
    });

    httpApi.addRoutes({
      integration: quizIntegration,
      methods: [apigw2.HttpMethod.GET],
      path: '/games/{game}',
    });

    httpApi.addRoutes({
      integration: quizIntegration,
      methods: [
        apigw2.HttpMethod.GET,
      ],
      path: '/games/{game}/questions',
    });

    httpApi.addRoutes({
      integration: quizIntegration,
      methods: [
        apigw2.HttpMethod.GET,
      ],
      path: '/games/{game}/questions/{question}',
    });

    httpApi.addRoutes({
      integration: quizIntegration,
      methods: [
        apigw2.HttpMethod.POST,
      ],
      path: '/games/{game}/questions/ask',
    });

    httpApi.addRoutes({
      integration: quizIntegration,
      methods: [
        apigw2.HttpMethod.POST,
      ],
      path: '/games/{game}/questions/answer',
    });

    this.api = httpApi;
    this.stage = stage;
  }
}
