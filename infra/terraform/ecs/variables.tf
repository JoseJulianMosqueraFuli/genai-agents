variable "project" {
  type = string
}

variable "environment" {
  type = string
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "ecr_repository_url" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "vpc_id" {
  type = string
}

variable "target_group_arn" {
  type = string
}

variable "listener_rule_arn" {
  type    = string
  default = ""
}

variable "alb_security_group_id" {
  type = string
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "task_cpu" {
  type    = number
  default = 512
}

variable "task_memory" {
  type    = number
  default = 1024
}

variable "llm_provider" {
  type    = string
  default = "bedrock"
}

variable "llm_model" {
  type    = string
  default = "gpt-4o-mini"
}

variable "bedrock_model_id" {
  type    = string
  default = "anthropic.claude-3-5-sonnet-20240620-v1"
}

variable "embedding_model" {
  type    = string
  default = "text-embedding-3-small"
}

variable "enable_guardrails" {
  type    = bool
  default = true
}

variable "openai_api_key_secret_arn" {
  type    = string
  default = ""
}

output "service_name" {
  value = aws_ecs_service.app.name
}

output "cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "task_definition_family" {
  value = aws_ecs_task_definition.app.family
}
