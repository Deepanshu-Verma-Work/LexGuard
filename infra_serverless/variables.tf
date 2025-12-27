variable "pinecone_api_key" {
  description = "API Key for Pinecone Vector DB"
  type        = string
  sensitive   = true
}

variable "github_token" {
  description = "GitHub Personal Access Token for Amplify"
  type        = string
  sensitive   = true
}
