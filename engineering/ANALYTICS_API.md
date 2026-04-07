api/v1/analytics/overview

{
  "success": true,
  "message": "Overview retrieved",
  "data": {
    "generated_at": "2026-04-03T12:22:18.697343Z",
    "period_from": "2026-03-01",
    "period_to": "2026-03-31",
    "total_appointments": 25,
    "completed": 7,
    "cancelled": 5,
    "no_show": 6,
    "pending": 1,
    "waiting": 6,
    "walk_ins": 6,
    "follow_ups": 10,
    "completion_rate": "28.00",
    "cancellation_rate": "20.00",
    "no_show_rate": "24.00",
    "total_revenue": "6700.00",
    "average_fee": "957.14",
    "peak_day": "2026-03-14",
    "peak_day_revenue": "3500.00",
    "unique_patients": 21,
    "new_patients": 21,
    "returning_patients": 0,
    "retention_rate": "0.00",
    "comparison": {
      "period_from": "2026-01-29",
      "period_to": "2026-02-28",
      "total_revenue_delta_pct": null,
      "total_appointments_delta_pct": null,
      "new_patients_delta_pct": null,
      "completion_rate_delta": "28.00"
    }
  }
}

api/v1/analytics/appointments
{
  "success": true,
  "message": "Appointment analytics retrieved",
  "data": {
    "generated_at": "2026-04-03T12:25:57.995226Z",
    "period_from": "2026-03-01",
    "period_to": "2026-03-31",
    "total_appointments": 25,
    "completion_rate": "28.00",
    "cancellation_rate": "20.00",
    "no_show_rate": "24.00",
    "breakdown": {
      "by_status": {
        "waiting": 6,
        "completed": 7,
        "cancelled": 5,
        "pending": 1,
        "no_show": 6
      },
      "by_type": {
        "follow_up": 10,
        "walk_in": 6,
        "regular": 9
      },
      "daily_breakdown": [
        {
          "date": "2026-03-14",
          "appointment_count": 7
        },
        {
          "date": "2026-03-15",
          "appointment_count": 8
        },
        {
          "date": "2026-03-16",
          "appointment_count": 3
        },
        {
          "date": "2026-03-17",
          "appointment_count": 0
        },
        {
          "date": "2026-03-18",
          "appointment_count": 3
        },
        {
          "date": "2026-03-19",
          "appointment_count": 2
        }
      ]
    },
    "comparison": {
      "period_from": "2026-01-29",
      "period_to": "2026-02-28",
      "total_appointments_delta_pct": null,
      "completion_rate_delta": "28.00",
      "no_show_rate_delta": "24.00"
    }
  }
}

api/v1/analytics/revenue
{
  "success": true,
  "message": "Revenue analytics retrieved",
  "data": {
    "generated_at": "2026-04-03T12:30:41.414661Z",
    "period_from": "2026-03-10",
    "period_to": "2026-03-14",
    "total_revenue": "5000.00",
    "average_per_appointment": "1000.00",
    "outstanding_amount": "0.00",
    "collection_rate": "100.00",
    "daily_breakdown": [
      {
        "date": "2026-03-10",
        "appointment_count": 1,
        "revenue": "1000.00"
      },
      {
        "date": "2026-03-11",
        "appointment_count": 1,
        "revenue": "250.00"
      },
      {
        "date": "2026-03-12",
        "appointment_count": 1,
        "revenue": "250.00"
      },
      {
        "date": "2026-03-13",
        "appointment_count": 1,
        "revenue": "500.00"
      },
      {
        "date": "2026-03-14",
        "appointment_count": 1,
        "revenue": "3000.00"
      }
    ],
    "comparison": {
      "period_from": "2026-03-05",
      "period_to": "2026-03-09",
      "total_revenue": "4000.00",
      "delta_pct": 25.00,
      "average_per_appointment": "1000.00"
    }
  }
}

api/v1/analytics/patients
{
  "success": true,
  "message": "Patient analytics retrieved",
  "data": {
    "generated_at": "2026-04-03T12:35:36.067615Z",
    "period_from": "2026-03-01",
    "period_to": "2026-03-31",
    "unique_patients": 21,
    "new_patients": 21,
    "returning_patients": 0,
    "retention_rate": "0.00",
    "top_procedures": [
      {
        "procedure": "Pericoronitis — wisdom tooth extraction recommended",
        "count": 2,
        "revenue": "2000.00"
      },
      {
        "procedure": "ANUG (Acute Necrotising Ulcerative Gingivitis)",
        "count": 1,
        "revenue": "500.00"
      },
      {
        "procedure": "Fractured cusp — crown placement advised",
        "count": 1,
        "revenue": "1500.00"
      },
      {
        "procedure": "xray",
        "count": 1,
        "revenue": "200.00"
      },
      {
        "procedure": "Periodontal disease — scaling and root planing required",
        "count": 1,
        "revenue": "1500.00"
      }
    ],
    "comparison": {
      "period_from": "2026-01-29",
      "period_to": "2026-02-28",
      "new_patients_delta_pct": null,
      "retention_rate_delta": "0.00"
    }
  }
}


api/v1/analytics/slots
{
  "success": true,
  "message": "Slot analytics retrieved",
  "data": {
    "generated_at": "2026-04-03T13:21:39.464255Z",
    "period_from": "2026-03-03",
    "period_to": "2026-04-03",
    "total_booked_slots": 8,
    "busiest_slot": "Thursday 14:00",
    "quietest_slot": "Tuesday 19:00",
    "heatmap": [
      {
        "day": "Monday",
        "slots": [
          {
            "hour": "08:00",
            "appointment_count": 10,
            "utilisation_rate": "100.00"
          },
          {
            "hour": "09:00",
            "appointment_count": 2,
            "utilisation_rate": "20.00"
          },
          {
            "hour": "10:00",
            "appointment_count": 3,
            "utilisation_rate": "30.00"
          },
          {
            "hour": "11:00",
            "appointment_count": 5,
            "utilisation_rate": "50.00"
          },
          {
            "hour": "12:00",
            "appointment_count": 7,
            "utilisation_rate": "70.00"
          },
          {
            "hour": "13:00",
            "appointment_count": 4,
            "utilisation_rate": "40.00"
          },
          {
            "hour": "14:00",
            "appointment_count": 5,
            "utilisation_rate": "50.00"
          },
          {
            "hour": "15:00",
            "appointment_count": 5,
            "utilisation_rate": "50.00"
          },
          {
            "hour": "16:00",
            "appointment_count": 3,
            "utilisation_rate": "30.00"
          },
          {
            "hour": "17:00",
            "appointment_count": 6,
            "utilisation_rate": "60.00"
          },
          {
            "hour": "18:00",
            "appointment_count": 4,
            "utilisation_rate": "40.00"
          },
          {
            "hour": "19:00",
            "appointment_count": 3,
            "utilisation_rate": "30.00"
          }
        ]
      },
      {
        "day": "Tuesday",
        ...
        // coninue for all days
      }
    ]
  }
}