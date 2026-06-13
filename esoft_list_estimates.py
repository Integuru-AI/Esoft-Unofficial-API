from curl_cffi import requests


def run(headers, user_input):
    """Pull estimates (customer requests) from the system with pagination."""
    page = user_input.get("page", 1)
    page_size = user_input.get("page_size", 100)

    # Validate inputs
    try:
        page = int(page)
        page_size = int(page_size)
    except (TypeError, ValueError):
        return {"status_code": 400, "body": {"error": "page and page_size must be integers"}}

    if page < 1:
        page = 1
    if page_size < 1 or page_size > 500:
        return {"status_code": 400, "body": {"error": "page_size must be between 1 and 500"}}

    start = (page - 1) * page_size

    try:
        response = _fetch_estimates(headers, start, page_size)
    except Exception as e:
        return {"status_code": 500, "body": {"error": str(e)}}

    # Check for auth failures
    if response.status_code in (302, 301):
        return {"status_code": 401, "body": {"error": "Session expired"}}

    if response.status_code == 403:
        return {"status_code": 403, "body": {"error": f"Access denied (status {response.status_code})"}}

    if response.status_code == 200:
        content_type = response.headers.get("content-type", "")
        if "json" not in content_type and "javascript" not in content_type:
            # Got HTML instead of JSON - likely a login page
            if "login" in response.text[:1000].lower():
                return {"status_code": 401, "body": {"error": "Session expired"}}
            return {"status_code": 500, "body": {"error": "Unexpected response format"}}

    if response.status_code != 200:
        return {"status_code": response.status_code, "body": {"error": f"Request failed with status {response.status_code}"}}

    result = response.json()

    total_records = result.get("recordsTotal", 0)
    total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0

    return {
        "status_code": 200,
        "body": {
            "estimates": result.get("data", []),
            "total_records": total_records,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
    }


# === PRIVATE ===


def _fetch_estimates(headers, start, length):
    """Fetch estimates from the customer requests endpoint with pagination."""
    base_url = BASE_URL

    request_headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{base_url}/customer/customer_requests",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }
    # Merge auth headers (Cookie) on top
    request_headers.update(headers)

    response = requests.get(
        f"{base_url}/customer/customer_requests",
        headers=request_headers,
        params={"start": start, "length": length},
        impersonate="chrome131",
        timeout=90,
        verify=False,
    )

    return response
