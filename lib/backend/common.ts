import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as pythonLambda from '@aws-cdk/aws-lambda-python-alpha';
import { Construct } from 'constructs';

export class Common extends Construct {
  public readonly commonLayer: lambda.ILayerVersion;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    const commonLayer = new pythonLambda.PythonLayerVersion(this, 'CommonLayer', {
      compatibleRuntimes: [
        lambda.Runtime.PYTHON_3_10,
      ],
      entry: 'lib/backend/common',
    });

    this.commonLayer = commonLayer;
  }
}
