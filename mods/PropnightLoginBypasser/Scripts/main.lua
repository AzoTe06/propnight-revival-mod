-- Wait for the Press Any Key widget, then call the same functions as Ctrl+Space once.
-- The widget can remain in UE's object array after the menu has opened, so do not auto-call twice.
local autoAttempted = false
local checks = 0
local maxChecks = 18

local function bypass(manual)
    ExecuteInGameThread(function()
        local ok, result = pcall(function()
            local screens = FindAllOf("W_PressAnyKeyScreen_C") or {}
            for _, screen in pairs(screens) do
                if screen:IsValid() and screen:GetFullName():find("GameEngine") then
                    if not manual and autoAttempted then return true end
                    if not manual then autoAttempted = true end
                    print("[PropnightLoginBypasser] Login screen found; sending bypass once.\n")
                    screen:PlayfabReady()
                    screen:AnyKeyPressed()
                    return true
                end
            end
            if manual then
                print("[PropnightLoginBypasser] Press Any Key screen not found yet.\n")
            elseif checks == 1 or checks == 9 or checks == maxChecks then
                print("[PropnightLoginBypasser] Waiting for Press Any Key screen.\n")
            end
            return false
        end)
        if not ok then print("[PropnightLoginBypasser] Bypass error: " .. tostring(result) .. "\n") end
    end)
end

RegisterKeyBind(Key.SPACE, { ModifierKey.CONTROL }, function() bypass(true) end)
RegisterKeyBind(Key.F8, function() bypass(true) end)

local function poll()
    checks = checks + 1
    if not autoAttempted then bypass(false) end
    if checks < maxChecks and not autoAttempted then
        ExecuteWithDelay(5000, poll)
    end
end

print("[PropnightLoginBypasser] Loaded. Automatic bypass waits for the login screen (up to 90 seconds); F8 or Ctrl+Space also works.\n")
ExecuteWithDelay(3000, poll)