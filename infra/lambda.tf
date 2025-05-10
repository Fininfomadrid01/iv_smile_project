// iv_smile_project/infra/lambda.tf
// Terraform resources for DynamoDB, IAM Roles, Lambdas y Event Source Mapping

############################################################
# 1) DynamoDB: Tablas RawPrices e ImpliedVols
############################################################

resource "aws_dynamodb_table" "raw_prices" {
  name             = "${var.environment}-raw-prices"
  billing_mode     = "PAY_PER_REQUEST"
  hash_key         = "id"
  stream_enabled   = true
  stream_view_type = "NEW_IMAGE"

  attribute {
    name = "id"
    type = "S"
  }

  tags = {
    Name        = "${var.environment}-raw-prices"
    Environment = var.environment
  }
}

resource "aws_dynamodb_table" "implied_vols" {
  name         = "${var.environment}-implied-vols"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  tags = {
    Name        = "${var.environment}-implied-vols"
    Environment = var.environment
  }
}

############################################################
# 2) IAM: Role y políticas para ejecuciones Lambda
############################################################

resource "aws_iam_role" "lambda_exec" {
  name = "${var.environment}-lambda-exec"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "lambda_dynamodb_policy" {
  name   = "${var.environment}-lambda-dynamodb-policy"
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = [
        "dynamodb:PutItem",
        "dynamodb:BatchWriteItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:DescribeStream",
        "dynamodb:GetRecords",
        "dynamodb:GetShardIterator",
        "dynamodb:ListStreams"
      ]
      Resource = [
        aws_dynamodb_table.raw_prices.stream_arn,
        "${aws_dynamodb_table.raw_prices.stream_arn}/*",
        aws_dynamodb_table.raw_prices.arn,
        aws_dynamodb_table.implied_vols.arn,
        "arn:aws:dynamodb:us-east-1:797161732660:table/futuros-table"
      ]
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_dynamodb_attach" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.lambda_dynamodb_policy.arn
}

############################################################
# 3) Lambdas: Scraper y Cálculo de IV
############################################################

data "aws_ecr_image" "scraper" {
  repository_name = aws_ecr_repository.app.name
  image_tag       = "scraper-latest"
}

data "aws_ecr_image" "iv_calc" {
  repository_name = aws_ecr_repository.app.name
  image_tag       = "iv-latest"
}

// Lambda Scraper en modo contenedor
resource "aws_lambda_function" "scraper" {
  function_name = var.scraper_lambda_name
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.app.repository_url}@${data.aws_ecr_image.scraper.image_digest}"
  role          = aws_iam_role.lambda_exec.arn
  timeout       = 900
  memory_size   = 2048

  environment {
    variables = {
      RAW_TABLE_NAME = aws_dynamodb_table.raw_prices.name
    }
  }
}

// Lambda IV Calc en modo contenedor
resource "aws_lambda_function" "iv_calc" {
  function_name = var.iv_lambda_name
  package_type  = "Image"
  image_uri     = "797161732660.dkr.ecr.us-east-1.amazonaws.com/iv-smile-app:iv-lambda"
  role          = aws_iam_role.lambda_exec.arn

  environment {
    variables = {
      RAW_TABLE_NAME = aws_dynamodb_table.raw_prices.name
      IV_TABLE_NAME  = aws_dynamodb_table.implied_vols.name
    }
  }

  timeout       = 120
  memory_size   = 512
}

// Lambda dev-api-lambda en modo contenedor
resource "aws_lambda_function" "dev_api_lambda" {
  function_name = "dev-api-lambda"
  package_type  = "Image"
  image_uri     = "797161732660.dkr.ecr.us-east-1.amazonaws.com/iv-smile-app:iv-api"
  role          = aws_iam_role.lambda_exec.arn
  timeout       = 60
  memory_size   = 512

  environment {
    variables = {
      RAW_TABLE_NAME = aws_dynamodb_table.raw_prices.name
      # Agrega aquí otras variables de entorno si las necesitas
    }
  }
}

resource "aws_lambda_function" "scraper_futuros" {
  function_name = "scraper-futuros-lambda"
  package_type  = "Image"
  image_uri     = "797161732660.dkr.ecr.us-east-1.amazonaws.com/iv-smile-app:futuros-lambda"
  role          = aws_iam_role.lambda_exec.arn
  timeout       = 900
  memory_size   = 2048

  environment {
    variables = {
      RAW_TABLE_NAME = aws_dynamodb_table.raw_prices.name
    }
  }
}

resource "aws_lambda_function" "scraper_v2" {
  function_name = "dev-scraper-lambda-v2"
  package_type  = "Image"
  image_uri     = "797161732660.dkr.ecr.us-east-1.amazonaws.com/iv-smile-app:opciones-lambda"
  role          = aws_iam_role.lambda_exec.arn
  timeout       = 900
  memory_size   = 2048

  environment {
    variables = {
      RAW_TABLE_NAME = aws_dynamodb_table.raw_prices.name
    }
  }
}

resource "aws_lambda_function" "api_embudo_lambda" {
  function_name = "api-embudo-lambda"
  package_type  = "Image"
  image_uri     = "797161732660.dkr.ecr.us-east-1.amazonaws.com/api-embudo-lambda:latest"
  role          = aws_iam_role.lambda_exec.arn

  environment {
    variables = {
      RAW_TABLE_NAME      = "dev-raw-prices"
      FUTUROS_TABLE_NAME  = "futuros-table"
      IV_TABLE_NAME       = "dev-implied-vols"
    }
  }
  timeout     = 30
  memory_size = 256
}

############################################################
# 4) Event Source Mapping: Stream de RawPrices → iv_calc Lambda
############################################################

resource "aws_lambda_event_source_mapping" "raw_to_iv" {
  depends_on        = [aws_iam_policy.lambda_dynamodb_policy]
  event_source_arn  = aws_dynamodb_table.raw_prices.stream_arn
  function_name     = aws_lambda_function.iv_calc.arn
  batch_size        = 100
  starting_position = "LATEST"
  enabled           = true
}