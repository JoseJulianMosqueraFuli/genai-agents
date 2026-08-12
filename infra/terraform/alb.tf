resource "aws_alb" "main" {
  name            = "${var.project}-${var.environment}-alb"
  internal        = false
  security_groups = [aws_security_group.alb.id]
  subnets         = module.vpc.public_subnet_ids

  enable_deletion_protection = false

  tags = { Name = "${var.project}-${var.environment}-alb" }
}

resource "aws_security_group" "alb" {
  name   = "${var.project}-${var.environment}-alb"
  vpc_id = module.vpc.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project}-${var.environment}-alb" }
}

resource "aws_alb_target_group" "app" {
  name        = "${var.project}-${var.environment}-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }

  tags = { Name = "${var.project}-${var.environment}-tg" }
}

resource "aws_alb_listener" "http" {
  load_balancer_arn = aws_alb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_alb_target_group.app.arn
  }
}
