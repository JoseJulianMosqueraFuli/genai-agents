variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project" {
  description = "Project name prefix"
  type        = string
  default     = "genai-agents"
}

variable "vpc_cidr" {
  description = "CIDR for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "azs" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 1
}

variable "task_cpu" {
  description = "Task CPU units (0.5 vCPU = 512)"
  type        = number
  default     = 512
}

variable "task_memory" {
  description = "Task memory in MB"
  type        = number
  default     = 1024
}

variable "llm_provider" {
  description = "LLM provider: openai or bedrock"
  type        = string
  default     = "bedrock"
}

variable "llm_model" {
  description = "LLM model id"
  type        = string
  default     = "gpt-4o-mini"
}

variable "bedrock_model_id" {
  description = "Bedrock model id (if llm_provider=bedrock)"
  type        = string
  default     = "anthropic.claude-3-5-sonnet-20240620-v1"
}

variable "openai_api_key" {
  description = "OpenAI API key (leave empty if using Bedrock). Use terraform.tfvars / secrets."
  type        = string
  default     = ""
  sensitive   = true
}

variable "embedding_model" {
  description = "Embeddings model"
  type        = string
  default     = "text-embedding-3-small"
}

variable "enable_guardrails" {
  description = "Enable guardrails"
  type        = bool
  default     = true
}
