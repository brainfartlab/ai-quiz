import { Construct } from 'constructs';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as targets from 'aws-cdk-lib/aws-route53-targets';
import * as apigw2 from '@aws-cdk/aws-apigatewayv2-alpha';

import { DomainSettings } from '../constants';

interface RoutingProps {
  api: apigw2.IHttpApi;
  environment: 'dev' | 'prd' | 'tst';
  hostedZoneId: string;
  netlifyDomain: string;
  path: string;
  stage: apigw2.HttpStage;
}

export class Routing extends Construct {
  public readonly hostedZone: route53.IHostedZone;

  constructor(scope: Construct, id: string, props: RoutingProps) {
    super(scope, id);

    const apiDomainName = `api.${props.environment}.${DomainSettings.domainName}`;

    const domainName = apigw2.DomainName.fromDomainNameAttributes(this, 'DomainName', {
      name: apiDomainName,
      regionalDomainName: DomainSettings.regionalDomainName,
      regionalHostedZoneId: DomainSettings.regionalHostedZoneId,
    });

    new apigw2.ApiMapping(this, 'QuizApiMapping', {
      api: props.api,
      apiMappingKey: props.path,
      domainName,
      stage: props.stage,
    });

    const hostedZone = route53.HostedZone.fromHostedZoneAttributes(this, 'HostedZone', {
      zoneName: `${props.environment}.brainfartlab.com`,
      hostedZoneId: props.hostedZoneId,
    });
    // const hostedZone = route53.HostedZone.fromHostedZoneId(this, 'HostedZone', props.hostedZoneId);
    new route53.CnameRecord(this, 'QuizFrontEndRecord', {
      recordName: `quiz.${props.environment}.${DomainSettings.domainName}`,
      zone: hostedZone,
      domainName: props.netlifyDomain,
    });
  }
}
