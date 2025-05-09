resource "aws_cloudwatch_event_rule" "daily_scraper" {
  name                = "${var.environment}-daily-scraper"
  description         = "Regla para ejecutar Lambdas de scraping diariamente a las 06:00 UTC"
  schedule_expression = "cron(0 6 * * ? *)"
}

resource "aws_cloudwatch_event_target" "scraper_futuros_target" {
  rule = aws_cloudwatch_event_rule.daily_scraper.name
  arn  = aws_lambda_function.scraper_futuros.arn
  input = jsonencode({})
}

resource "aws_cloudwatch_event_target" "scraper_opciones_target" {
  rule = aws_cloudwatch_event_rule.daily_scraper.name
  arn  = aws_lambda_function.scraper_v2.arn
  input = jsonencode({})
}

resource "aws_lambda_permission" "allow_eventbridge_invoke_scraper_futuros" {
  statement_id  = "AllowEventBridgeInvokeFuturos"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scraper_futuros.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_scraper.arn
}

resource "aws_lambda_permission" "allow_eventbridge_invoke_scraper_opciones" {
  statement_id  = "AllowEventBridgeInvokeOpciones"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scraper_v2.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_scraper.arn
}