resource "aws_cloudwatch_event_rule" "daily_scraper" {
  name                = "${var.environment}-daily-scraper"
  description         = "Regla para ejecutar scraper Lambda diariamente a las 06:00 UTC"
  schedule_expression = "cron(0 6 * * ? *)"
}

resource "aws_cloudwatch_event_target" "scraper_target" {
  rule = aws_cloudwatch_event_rule.daily_scraper.name
  arn  = aws_lambda_function.scraper.arn
  input = jsonencode({})
}

resource "aws_lambda_permission" "allow_eventbridge_invoke_scraper" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scraper.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_scraper.arn
} 