module Api exposing (apiBaseUrl, httpErrorToString)

import Http


apiBaseUrl : String
apiBaseUrl =
    "http://localhost:8000"


httpErrorToString : Http.Error -> String
httpErrorToString error =
    case error of
        Http.BadUrl url ->
            "Bad URL: " ++ url

        Http.Timeout ->
            "Request timed out"

        Http.NetworkError ->
            "Network error"

        Http.BadStatus code ->
            "Server error (" ++ String.fromInt code ++ ")"

        Http.BadBody message ->
            "Unexpected response: " ++ message
