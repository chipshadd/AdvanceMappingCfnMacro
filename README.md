# AdvancedEnvMap Cfn macro
The Mappings block and FindInMap function in Cloudformation only support non-complex data. This transformation macro will enable functionality similar to a Mappings block, but allows for complex data allowing for different config blocks on a per environment basis.

## How to install
AWS Sam CLI is required.
`sam deploy --guided` and follow the prompts according to your AWS account

## How to use it
1. Add `AdvancedMapping` to your transforms in your template
```yaml
Transform:
  - "AdvancedMappingMacro"
```
2. Add a parameter to your template denoting the environment's name (if it doesn't exist already):
e.g.
```yaml
Parameters:
  EnvironmentName:
    Type: String
    AllowedValues:
    - dev
    - staging
    - production
```
3. Nest any config block under a `AdvancedMapping.${ENV_NAME}` key. Create multiple copies of that config block under different ${ENV_NAME} keys:
```yaml
AdvancedMapping:
	dev:
		<Set of properties or resources>
  production:
    <Set of same properties or resources with different configurations>
```

**EnvironmentName**
The identifier of the enviroment.  The macro will lookup this parameter's value that you passed to your template, and proceed to look for that value within the template to make the necessary transformations.

Use `allOthers` as the environment name to use that set of configurations as the default.
If the passed in value to the `EnvironmentName` parameter does not match anything found under the `AdvancedMapping` key, then anything under the `AdvancedMapping` key will be removed from the template (it will be assumed that the configs within do not apply to the supplied environment)

**Set of properties**
Insert any cloudformation configuration of any depth and any complexity. Configurations can range from a top level logical ID under `Resources` (or any other root level key) to a single key and value nested anywhere within the `Properties` key of any logical ID.

### Example 1:
This is for a CodeDeploy hook for ECS blue/green deployment. In production we want to run a canary deployment while in lower environments we would want to blast the new code in without waiting.

Raw template:
```yaml
Parameters:
  EnvironmentName:
    Type: String
Transform:
	- "AdvancedEnvMappingMacro"
Hooks:
  CodeDeployBlueGreenHook:
    Type: "AWS::CodeDeploy::BlueGreen"
    Properties:
      TrafficRoutingConfig:
	      AdvancedMapping:
	        production:
			      Type: TimeBasedCanary
	          TimeBasedCanary:
	            StepPercentage: 25
	            BakeTimeMins: 1
	        allOthers:
	          Type: AllAtOnce
      LifecycleEventHooks:
        AfterAllowTestTraffic: !Ref DeploymentHook
      ServiceRole: !Ref DeploymentRole
      Applications:
        - Target:
            Type: "AWS::ECS::Service"
            LogicalID: ECSDemoService
<<truncated for brevity>>
```

Resulting template if EnvironmentName == 'production':
```yaml
Parameters:
  EnvironmentName:
    Type: String
Transform:
	- "AdvancedEnvMappingMacro"
Hooks:
  CodeDeployBlueGreenHook:
    Type: "AWS::CodeDeploy::BlueGreen"
    Properties:
      TrafficRoutingConfig:
	     Type: TimeBasedCanary
	     TimeBasedCanary:
		     StepPercentage: 25
		     BakeTimeMins: 1
      LifecycleEventHooks:
	      AfterAllowTestTraffic: !Ref DeploymentHook
      ServiceRole: !Ref DeploymentRole
      Applications:
        - Target:
            Type: "AWS::ECS::Service"
            LogicalID: ECSDemoService
<<truncated for brevity>>
```

### Example 2
Since we don't really need to use `LifecycleEventHookss where we are not planning on doing canary deployments, let's not include it in the template for deployments to lower environments.

Raw template:
```yaml
Parameters:
  EnvironmentName:
    Type: String
Transform:
	- "AdvancedEnvMappingMacro"
Hooks:
  CodeDeployBlueGreenHook:
    Type: "AWS::CodeDeploy::BlueGreen"
    Properties:
      TrafficRoutingConfig:
	      AdvancedMapping:
	        production:
			      Type: TimeBasedCanary
	          TimeBasedCanary:
	            StepPercentage: 25
	            BakeTimeMins: 1
	        allOthers:
	          Type: AllAtOnce
	    AdvancedMapping:
		    production:
		      LifecycleEventHooks:
		        AfterAllowTestTraffic: !Ref DeploymentHook
      ServiceRole: !Ref DeploymentRole
      Applications:
        - Target:
            Type: "AWS::ECS::Service"
            LogicalID: ECSDemoService
<<truncated for brevity>>
```

Resulting template if EnvironmentName != 'production':
```yaml
Parameters:
  EnvironmentName:
    Type: String
Transform:
	- "AdvancedEnvMappingMacro"
Hooks:
  CodeDeployBlueGreenHook:
    Type: "AWS::CodeDeploy::BlueGreen"
    Properties:
      TrafficRoutingConfig:
	     Type: AllAtOnce
      ServiceRole: !Ref DeploymentRole
      Applications:
        - Target:
            Type: "AWS::ECS::Service"
            LogicalID: ECSDemoService
<<truncated for brevity>>
```
- Under `TrafficRoutingConfig`, `production` was the only environment configured and did not match what was passed in, so it defaulted to the value defined under the `allOthers` key
- The `LifecycleEventHooks` key has been removed from the template as no configs were defined for the `EnvironmentName` that was passed in

## Caveats
- Do not nest the macro within itself, create a separate `EnvironmentName` key and repeat all the configs while incorporating the differences