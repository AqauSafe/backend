#include "aquasafe_core.h"

#ifdef ARDUINO
#include <mbedtls/md.h>
#else
#include <openssl/evp.h>
#include <openssl/hmac.h>
#endif

namespace aquasafe {
namespace {

std::string to_hex(const unsigned char* data, std::size_t length) {
    static const char* digits = "0123456789abcdef";
    std::string out;
    out.resize(length * 2);
    for (std::size_t i = 0; i < length; ++i) {
        out[i * 2] = digits[(data[i] >> 4) & 0x0f];
        out[i * 2 + 1] = digits[data[i] & 0x0f];
    }
    return out;
}

bool constant_time_equal(std::string_view a, std::string_view b) {
    if (a.size() != b.size()) {
        return false;
    }
    unsigned char diff = 0;
    for (std::size_t i = 0; i < a.size(); ++i) {
        diff |= static_cast<unsigned char>(a[i] ^ b[i]);
    }
    return diff == 0;
}

bool parse_utc_timestamp(std::string_view text, std::int64_t& epoch) {
    if (text.size() < 19 || text[4] != '-' || text[7] != '-' ||
        (text[10] != 'T' && text[10] != ' ') || text[13] != ':' || text[16] != ':') {
        return false;
    }
    auto number = [&](std::size_t offset, std::size_t length) -> int {
        int value = 0;
        for (std::size_t i = 0; i < length; ++i) {
            const char c = text[offset + i];
            if (c < '0' || c > '9') {
                return -1;
            }
            value = value * 10 + (c - '0');
        }
        return value;
    };
    const int year = number(0, 4);
    const int month = number(5, 2);
    const int day = number(8, 2);
    const int hour = number(11, 2);
    const int minute = number(14, 2);
    const int second = number(17, 2);
    if (year < 1970 || month < 1 || month > 12 || day < 1 || day > 31 ||
        hour < 0 || hour > 23 || minute < 0 || minute > 59 ||
        second < 0 || second > 60) {
        return false;
    }
    const int adjusted_year = year - (month <= 2 ? 1 : 0);
    const int era = (adjusted_year >= 0 ? adjusted_year : adjusted_year - 399) / 400;
    const unsigned year_of_era = static_cast<unsigned>(adjusted_year - era * 400);
    const unsigned day_of_year =
        static_cast<unsigned>((153 * (month + (month > 2 ? -3 : 9)) + 2) / 5 + day - 1);
    const unsigned day_of_era =
        year_of_era * 365 + year_of_era / 4 - year_of_era / 100 + day_of_year;
    const std::int64_t days = static_cast<std::int64_t>(era) * 146097 +
                              static_cast<std::int64_t>(day_of_era) - 719468;
    epoch = days * 86400 + hour * 3600 + minute * 60 + second;
    return true;
}

std::string json_quote(std::string_view value) {
    std::string out;
    out.reserve(value.size() + 2);
    out.push_back('"');
    for (const char c : value) {
        switch (c) {
            case '"':
                out.append("\\\"");
                break;
            case '\\':
                out.append("\\\\");
                break;
            case '\n':
                out.append("\\n");
                break;
            case '\r':
                out.append("\\r");
                break;
            case '\t':
                out.append("\\t");
                break;
            default:
                if (static_cast<unsigned char>(c) < 0x20) {
                    char escaped[7];
                    std::snprintf(escaped, sizeof(escaped), "\\u%04x",
                                  static_cast<unsigned char>(c));
                    out.append(escaped);
                } else {
                    out.push_back(c);
                }
        }
    }
    out.push_back('"');
    return out;
}

std::string command_canonical(const CommandEnvelope& command, std::string_view device_id) {
    std::string canonical;
    canonical.reserve(command.command_id.size() + command.command_type.size() +
                      command.expires_at.size() + command.payload.size() +
                      device_id.size() + 8);
    canonical.append(command.command_id);
    canonical.push_back('\n');
    canonical.append(device_id);
    canonical.push_back('\n');
    canonical.append(command.command_type);
    canonical.push_back('\n');
    canonical.append(command.expires_at);
    canonical.push_back('\n');
    canonical.append(command.payload);
    return canonical;
}

}  // namespace

#ifdef ARDUINO
std::string sha256_hex(std::string_view message) {
    unsigned char digest[32];
    mbedtls_md_context_t context;
    mbedtls_md_init(&context);
    mbedtls_md_setup(&context, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 0);
    mbedtls_md_starts(&context);
    mbedtls_md_update(&context, reinterpret_cast<const unsigned char*>(message.data()), message.size());
    mbedtls_md_finish(&context, digest);
    mbedtls_md_free(&context);
    return to_hex(digest, sizeof(digest));
}

std::string hmac_sha256_hex(std::string_view key, std::string_view message) {
    unsigned char digest[32];
    mbedtls_md_context_t context;
    mbedtls_md_init(&context);
    mbedtls_md_setup(&context, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 1);
    mbedtls_md_hmac_starts(&context, reinterpret_cast<const unsigned char*>(key.data()), key.size());
    mbedtls_md_hmac_update(&context, reinterpret_cast<const unsigned char*>(message.data()), message.size());
    mbedtls_md_hmac_finish(&context, digest);
    mbedtls_md_free(&context);
    return to_hex(digest, sizeof(digest));
}
#else
std::string sha256_hex(std::string_view message) {
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int length = 0;
    EVP_MD_CTX* context = EVP_MD_CTX_new();
    EVP_DigestInit_ex(context, EVP_sha256(), nullptr);
    EVP_DigestUpdate(context, message.data(), message.size());
    EVP_DigestFinal_ex(context, digest, &length);
    EVP_MD_CTX_free(context);
    return to_hex(digest, length);
}

std::string hmac_sha256_hex(std::string_view key, std::string_view message) {
    unsigned char digest[EVP_MAX_MD_SIZE];
    unsigned int length = 0;
    HMAC(EVP_sha256(), key.data(), static_cast<int>(key.size()),
         reinterpret_cast<const unsigned char*>(message.data()), message.size(), digest, &length);
    return to_hex(digest, length);
}
#endif

bool verify_hmac_sha256(std::string_view key, std::string_view message, std::string_view signature_hex) {
    return constant_time_equal(hmac_sha256_hex(key, message), signature_hex);
}

bool command_is_expired(const CommandEnvelope& command, std::string_view now_iso8601) {
    std::int64_t now_epoch = 0;
    std::int64_t expires_epoch = 0;
    if (!parse_utc_timestamp(now_iso8601, now_epoch) ||
        !parse_utc_timestamp(command.expires_at, expires_epoch)) {
        return true;
    }
    return now_epoch >= expires_epoch;
}

bool verify_command(const CommandEnvelope& command, std::string_view device_id, std::string_view secret) {
    return verify_hmac_sha256(secret, command_canonical(command, device_id), command.signature);
}

std::string telemetry_json(std::string_view device_id, std::string_view message_id,
                           const TelemetryRecord& record) {
    char buffer[512];
    const int written = std::snprintf(
        buffer, sizeof(buffer),
        "{\"message_id\":\"%.*s\",\"device_id\":\"%.*s\",\"recorded_at\":%lu,"
        "\"temperature\":%.2f,\"oxygen\":%.2f,\"ph\":%.2f,\"level\":%.2f",
        static_cast<int>(message_id.size()), message_id.data(),
        static_cast<int>(device_id.size()), device_id.data(),
        static_cast<unsigned long>(record.recorded_at), record.temperature_c,
        record.oxygen_mg_l, record.ph, record.water_level_pct);
    if (written > 0 && static_cast<std::size_t>(written) < sizeof(buffer)) {
        if (record.has_turbidity) {
            std::snprintf(buffer + written, sizeof(buffer) - written,
                          ",\"turbidityNtu\":%.2f}", record.turbidity_ntu);
        } else {
            std::snprintf(buffer + written, sizeof(buffer) - written, "}");
        }
    }
    return std::string(buffer);
}

std::string telemetry_envelope_json(std::string_view device_id, std::string_view message_id,
                                    const TelemetryRecord& record, std::string_view secret) {
    const std::string body = telemetry_json(device_id, message_id, record);
    return "{\"payload\":" + json_quote(body) + ",\"signature\":\"" +
           hmac_sha256_hex(secret, body) + "\"}";
}

}  // namespace aquasafe
