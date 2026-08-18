resource "aws_ecs_cluster" "main" {
  name = "${var.project}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 100
  }
}

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.project}-${var.environment}"
  retention_in_days = 14
}

resource "aws_ecs_task_definition" "app" {
  family                   = "${var.project}-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "app"
      image     = "${var.ecr_repository_url}:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "APP_NAME", value = var.project },
        { name = "ENVIRONMENT", value = var.environment },
        { name = "LLM_PROVIDER", value = var.llm_provider },
        { name = "LLM_MODEL", value = var.llm_model },
        { name = "BEDROCK_MODEL_ID", value = var.bedrock_model_id },
        { name = "EMBEDDING_MODEL", value = var.embedding_model },
        { name = "ENABLE_GUARDRAILS", value = tostring(var.enable_guardrails) },
        { name = "LOG_LEVEL", value = "INFO" },
      ]
      secrets = var.llm_provider == "openai" ? [
        { name = "OPENAI_API_KEY", valueFrom = var.openai_api_key_secret_arn }
      ] : []
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = var.project
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)\" || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 15
      }
    }
  ])

  tags = {
    Name = "${var.project}-${var.environment}-task"
  }
}

resource "aws_ecs_service" "app" {
  name            = "${var.project}-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count

  # Run on Fargate Spot. NOTE: `launch_type` and `capacity_provider_strategy` are
  # mutually exclusive — setting launch_type = "FARGATE" would silently ignore the
  # cluster's Spot default and run on-demand. So we pin the strategy here instead.
  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = var.fargate_spot_weight
    base              = 0
  }

  # Optional on-demand base for availability during Spot reclamation. Defaults to 0
  # (pure Spot); set fargate_base_count > 0 to keep N tasks always on-demand.
  dynamic "capacity_provider_strategy" {
    for_each = var.fargate_base_count > 0 ? [1] : []
    content {
      capacity_provider = "FARGATE"
      weight            = 0
      base              = var.fargate_base_count
    }
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "app"
    container_port   = 8000
  }

  depends_on = [
    var.listener_rule_arn,
    aws_ecs_cluster_capacity_providers.main,
  ]

  tags = {
    Name = "${var.project}-${var.environment}-service"
  }
}

resource "aws_security_group" "ecs_tasks" {
  name   = "${var.project}-${var.environment}-ecs-tasks"
  vpc_id = var.vpc_id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [var.alb_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project}-${var.environment}-ecs-tasks" }
}
