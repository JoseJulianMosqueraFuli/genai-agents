module "vpc" {
  source      = "./vpc"
  project     = var.project
  environment = var.environment
  vpc_cidr    = var.vpc_cidr
  azs         = var.azs
}

module "ecs" {
  source = "./ecs"

  project                 = var.project
  environment             = var.environment
  region                  = var.region
  ecr_repository_url      = aws_ecr_repository.app.repository_url
  private_subnet_ids      = module.vpc.private_subnet_ids
  vpc_id                  = module.vpc.vpc_id
  target_group_arn        = aws_alb_target_group.app.arn
  listener_rule_arn       = aws_alb_listener.http.arn
  alb_security_group_id   = aws_security_group.alb.id
  desired_count           = var.desired_count
  fargate_spot_weight     = var.fargate_spot_weight
  fargate_base_count      = var.fargate_base_count
  task_cpu                = var.task_cpu
  task_memory             = var.task_memory
  llm_provider            = var.llm_provider
  bedrock_model_id        = var.bedrock_model_id
  bedrock_embedding_model = var.bedrock_embedding_model
  vector_backend          = var.vector_backend
  s3_vectors_bucket       = var.s3_vectors_bucket
  s3_vectors_index        = var.s3_vectors_index
  enable_guardrails       = var.enable_guardrails
}

output "alb_dns" {
  value = aws_alb.main.dns_name
}

output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}
