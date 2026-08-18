# Plan-only tests: run with `terraform test`. Uses a mocked AWS provider,
# so no credentials or real AWS resources are required.
mock_provider "aws" {}

run "vpc_resources_exist" {
  command = plan

  variables {
    project     = "genai-agents"
    environment = "test"
    region      = "us-east-1"
    azs         = ["us-east-1a", "us-east-1b"]
  }

  assert {
    condition     = length(module.vpc.public_subnet_ids) == 2
    error_message = "Expected 2 public subnets"
  }
  assert {
    condition     = length(module.vpc.private_subnet_ids) == 2
    error_message = "Expected 2 private subnets"
  }
}

run "ecr_repository_config" {
  command = plan

  variables {
    project     = "genai-agents"
    environment = "test"
    region      = "us-east-1"
  }

  assert {
    condition     = aws_ecr_repository.app.name == "genai-agents-test"
    error_message = "ECR repository name must follow project-environment"
  }
  assert {
    condition     = aws_ecr_repository.app.force_delete == true
    error_message = "ECR force_delete should be true for a dev repo"
  }
  assert {
    condition     = aws_ecr_repository.app.image_scanning_configuration[0].scan_on_push == true
    error_message = "ECR scan_on_push must be enabled"
  }
}

run "alb_health_check" {
  command = plan

  variables {
    project     = "genai-agents"
    environment = "test"
    region      = "us-east-1"
  }

  assert {
    condition     = aws_alb_target_group.app.port == 8000
    error_message = "Target group must point to container port 8000"
  }
  assert {
    condition     = aws_alb_target_group.app.health_check[0].path == "/health"
    error_message = "Health check must hit /health"
  }
  assert {
    condition     = aws_alb_target_group.app.health_check[0].matcher == "200"
    error_message = "Health check must accept status 200"
  }
}

run "ecs_fargate_spot_strategy" {
  command = plan

  variables {
    project       = "genai-agents"
    environment   = "test"
    region        = "us-east-1"
    llm_provider  = "bedrock"
    desired_count = 1
  }

  assert {
    condition     = module.ecs.cluster_name == "genai-agents-test"
    error_message = "ECS cluster name must follow project-environment"
  }
  assert {
    condition     = module.ecs.task_definition_family == "genai-agents-test"
    error_message = "Task definition family must follow project-environment"
  }

  # The actual Spot guarantee: the service must run via the FARGATE_SPOT capacity
  # provider strategy and must NOT pin launch_type (which would silently force
  # on-demand and bypass Spot).
  assert {
    condition     = contains(module.ecs.capacity_providers, "FARGATE_SPOT")
    error_message = "ECS service must use the FARGATE_SPOT capacity provider"
  }
  # Default is pure Spot: no on-demand FARGATE provider attached. A pinned
  # launch_type would produce an empty strategy here, so this also guards against
  # the launch_type regression that silently bypasses Spot.
  assert {
    condition     = !contains(module.ecs.capacity_providers, "FARGATE")
    error_message = "Default deployment must be pure Spot (no on-demand FARGATE)"
  }
}

run "ecs_fargate_base_ondemand_optional" {
  command = plan

  variables {
    project            = "genai-agents"
    environment        = "test"
    region             = "us-east-1"
    llm_provider       = "bedrock"
    fargate_base_count = 2
  }

  # With a non-zero base, both Spot and on-demand FARGATE providers are attached.
  assert {
    condition     = contains(module.ecs.capacity_providers, "FARGATE_SPOT") && contains(module.ecs.capacity_providers, "FARGATE")
    error_message = "A non-zero base must add an on-demand FARGATE provider alongside Spot"
  }
}
