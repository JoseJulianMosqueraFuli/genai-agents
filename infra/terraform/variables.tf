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

variable "fargate_spot_weight" {
  description = "Relative weight of FARGATE_SPOT in the service capacity provider strategy"
  type        = number
  default     = 100
}

variable "fargate_base_count" {
  description = "Tasks to always run on on-demand FARGATE (0 = pure Spot)"
  type        = number
  default     = 0
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
  description = "LLM provider (Bedrock only)"
  type        = string
  default     = "bedrock"
}

variable "bedrock_model_id" {
  description = "Bedrock generation model id (Amazon Nova via inference profile)"
  type        = string
  default     = "us.amazon.nova-pro-v1:0"
}

variable "bedrock_embedding_model" {
  description = "Bedrock embeddings model (Amazon Titan Text Embeddings V2)"
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "vector_backend" {
  description = "RAG vector store backend: in_memory or s3_vectors"
  type        = string
  default     = "in_memory"
}

variable "s3_vectors_bucket" {
  description = "S3 Vectors bucket name (empty = disabled; app creates it via SDK)"
  type        = string
  default     = ""
}

variable "s3_vectors_index" {
  description = "S3 Vectors index name"
  type        = string
  default     = "docs"
}

variable "enable_guardrails" {
  description = "Enable guardrails"
  type        = bool
  default     = true
}
