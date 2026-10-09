-- Local level loading test. No hooks or asset-registry calls.
-- Map path verified against this installation's pak index.
local source = debug.getinfo(1, "S").source:gsub("^@", ""):gsub("\\", "/")
local commandFile = source:match("^(.*)/Mods/") .. "/revival-map-command.txt"
local abbey = "/Game/Maps/GeneralLevels/Horror_Abbey/Big_Abbey/Big_Abbey_Main"
local function log(s) print("[LocalMap] " .. s .. "\n") end
local lanRole = nil
local pollCount = 0
local observedKiller = nil
local observedKillerAt = 0
local checkedKiller = nil
local blockedLobby = nil
local reportedLobbyRepair = {}
-- Paths confirmed in this build's loaded Unreal object dump.
local firstPersonAnimClasses = {
    ClownKiller_C = "/Game/Characters/Blueprints/Killer/Clown/Animation/FP/ClownFPPABP.ClownFPPABP_C",
    Possum_C = "/Game/Characters/Blueprints/Killer/Possum/Animation/FPP/PossumFPPABP.PossumFPPABP_C",
    Rabbit_C = "/Game/Characters/Blueprints/Killer/Rabbit/Animation/FP/BP/FPRabbitBPAnim.FPRabbitBPAnim_C",
    Nina_C = "/Game/Characters/Blueprints/Killer/Nina/Animations/FP/BP/MaddyAnimFP.MaddyAnimFP_C",
    SheetMan_C = "/Game/Characters/Blueprints/Killer/Sheet/Anim/FP/SheetAnimFP.SheetAnimFP_C",
    Vampire_C = "/Game/Characters/Blueprints/Killer/Vampire/FP/Mesh/FP_Vampire_Skeleton_AnimBlueprint.FP_Vampire_Skeleton_AnimBlueprint_C",
    Samurai_C = "/Game/Characters/Blueprints/Killer/Samurai/Animations/FP/BPA_FP_Samurai.BPA_FP_Samurai_C",
    Doppelganger_C = "/Game/Characters/Blueprints/Killer/Doppelganger/Animations/FPP/Doppel_FPP_AnimBP.Doppel_FPP_AnimBP_C",
    Granny_C = "/Game/Characters/Blueprints/Killer/Granny/animation/FP/FPGrannyAnimBP.FPGrannyAnimBP_C",
}
-- KillerType.uasset/.uexp enumerator order from this build (Rabbit = 4).
-- Each pair is the lobby body mesh and its matching lobby animation class.
local lobbyKillerLooks = {
    [0] = {"Banshee", "/Game/Characters/Blueprints/Killer/Banshee/Anim/tp/NewFolder2/banshee_a-pose.banshee_a-pose", "/Game/Characters/Blueprints/Killer/Banshee/Anim/tp/BanshAnimBP.BanshAnimBP_C"},
    [1] = {"Impostor", "/Game/Characters/Blueprints/Killer/Doppelganger/Model/Doppel_A_Pose.Doppel_A_Pose_Lockup_low", "/Game/Characters/Blueprints/Killer/Doppelganger/Animations/DoppelLobby.DoppelLobby_C"},
    [2] = {"Granny", "/Game/Characters/Blueprints/Killer/Granny/Grandma_Facerig.Grandma_Facerig", "/Game/Characters/Blueprints/Killer/Granny/Grandma_Facerig_Skeleton_AnimBlueprint_Lobby.Grandma_Facerig_Skeleton_AnimBlueprint_Lobby_C"},
    [3] = {"Vampire", "/Game/Characters/Blueprints/Killer/Vampire/TP/Mesh/Vampire_apos.Vampire_apos", "/Game/Characters/Blueprints/Killer/Vampire/TP/Mesh/VampireLobbyAnimBP.VampireLobbyAnimBP_C"},
    [4] = {"Rabbit", "/Game/Characters/Blueprints/Killer/Rabbit/Model/rabbit_a-pose.rabbit_a-pose", "/Game/Characters/Blueprints/Killer/Rabbit/Animation/TP/BP/LobbyRabbitAnimBP.LobbyRabbitAnimBP_C"},
    [5] = {"Sheet", "/Game/Characters/Blueprints/Killer/Sheet/Model/sheet_man.sheet_man", "/Game/Characters/Blueprints/Killer/Sheet/Anim/TP/bp/SheetAnimBP_Lobby.SheetAnimBP_Lobby_C"},
    [6] = {"Maddy", "/Game/Characters/Blueprints/Killer/Nina/Model/Nina_A_Pose.Nina_A_Pose", "/Game/Characters/Blueprints/Killer/Nina/Animations/NinaAnimLobby.NinaAnimLobby_C"},
    [7] = {"Possum", "/Game/Characters/Blueprints/Killer/Possum/Model/TP/Possum_a-pose.Possum_a-pose", "/Game/Characters/Blueprints/Killer/Possum/Animation/TPP/Possum_TPP_Lobby.Possum_TPP_Lobby_C"},
    [8] = {"Granny special", "/Game/Characters/Blueprints/Killer/Granny/Yaga/Granny_skin_02_yaga_a-pose.Granny_skin_02_yaga_a-pose", "/Game/Characters/Blueprints/Killer/Granny/Grandma_Facerig_Skeleton_AnimBlueprint_Lobby.Grandma_Facerig_Skeleton_AnimBlueprint_Lobby_C"},
    [9] = {"Impostor special", "/Game/Characters/Blueprints/Killer/Doppelganger/Model/Skins/Puppet/imposter_skin_02_puppet_a-pose.imposter_skin_02_puppet_a-pose", "/Game/Characters/Blueprints/Killer/Doppelganger/Animations/DoppelLobby.DoppelLobby_C"},
    [10] = {"Banshee special", "/Game/Characters/Blueprints/Killer/Banshee/Anim/tp/NewFolder2/Banshee_Nurse.Banshee_Nurse", "/Game/Characters/Blueprints/Killer/Banshee/Anim/tp/BanshAnimBP.BanshAnimBP_C"},
    [11] = {"Vampire special", "/Game/Characters/Blueprints/Killer/Vampire/Skin/TP/Hunt/akasha_skin_Hunt_a-pose.akasha_skin_Hunt_a-pose", "/Game/Characters/Blueprints/Killer/Vampire/TP/Mesh/VampireLobbyAnimBP.VampireLobbyAnimBP_C"},
    [12] = {"Clown", "/Game/Characters/Blueprints/Killer/Clown/Model/Clown_a-pose.Clown_a-pose", "/Game/Characters/Blueprints/Killer/Clown/Animation/TP/Lobby_Intro/ClownLobbyABP.ClownLobbyABP_C"},
    [13] = {"Samurai", "/Game/Characters/Blueprints/Killer/Samurai/Model/TP/Samurai_a-poseY.Samurai_a-poseY", "/Game/Characters/Blueprints/Killer/Samurai/Animations/TP/BPA_Samurai_Lobby.BPA_Samurai_Lobby_C"},
}
local function describeObject(value)
    if not value or not value:IsValid() then return "missing" end
    return value:GetFullName()
end
local function readObject(parent, field)
    if not parent or not parent:IsValid() then return nil end
    local ok, value = pcall(function() return parent[field] end)
    if ok and value and value:IsValid() then return value end
    return nil
end
local function readValue(parent, field)
    if not parent or not parent:IsValid() then return "missing" end
    local ok, value = pcall(function() return parent[field] end)
    return ok and tostring(value) or "unreadable"
end
-- FindAllOf walks the whole object array, which stalls the game thread when it
-- runs often. Objects the mod polls are recorded as they are created instead.
local function track(list, object)
    list[#list + 1] = object
end
local function prune(list)
    for i = #list, 1, -1 do
        if not list[i]:IsValid() then table.remove(list, i) end
    end
    return list
end
local controllers = {}
NotifyOnNewObject("/Script/Engine.PlayerController", function(pc) track(controllers, pc) end)
local function localController()
    for _, pc in ipairs(prune(controllers)) do
        local ok, isLocal = pcall(function() return pc:IsLocalController() end)
        if ok and isLocal and pc:GetFullName():find("PersistentLevel", 1, true) then return pc end
    end
end
local killerClassPath = "/Game/Characters/Blueprints/Killer/KillerMasterBP.KillerMasterBP_C"
local survivorClassPath = "/Game/Characters/Blueprints/Survivor/SurvivorMasterBP.SurvivorMasterBP_C"
local loadedClasses = {}
local function loadedClass(path)
    local cls = loadedClasses[path]
    if cls and cls:IsValid() then return cls end
    cls = StaticFindObject(path)
    if cls and cls:IsValid() then loadedClasses[path] = cls; return cls end
end
local function pawnIs(pawn, classPath)
    local cls = loadedClass(classPath)
    if not pawn or not cls then return false end
    local ok, result = pcall(function() return pawn:IsA(cls) end)
    return ok and result
end
local function localPawn()
    return readObject(localController(), "Pawn")
end
local function localKiller()
    local pawn = localPawn()
    if pawnIs(pawn, killerClassPath) then return pawn end
end
local function inMatch()
    local pawn = localPawn()
    return pawnIs(pawn, killerClassPath) or pawnIs(pawn, survivorClassPath)
end
-- Lobby blueprint classes load with the map, so their creation notifications
-- are registered once the class exists, with a single scan for earlier objects.
local lobbyTracked = {
    { class = "/Game/CameraAssets/CinematicExamples/LobbyPlayerMesh.LobbyPlayerMesh_C", short = "LobbyPlayerMesh_C", objects = {} },
    { class = "/Game/Blueprints/MiniLobby/W_MiniLobby.W_MiniLobby_C", short = "W_MiniLobby_C", objects = {} },
    { class = "/Game/UI/InGameUI/TabStat/TabSocial/PlayerScore_ReportWindow.PlayerScore_ReportWindow_C", short = "PlayerScore_ReportWindow_C", objects = {} },
    { class = "/Game/Blueprints/MiniLobby/LevelUI/WBP_LevelProgress.WBP_LevelProgress_C", short = "WBP_LevelProgress_C", objects = {} },
    { class = "/Game/Blueprints/MiniLobby/WBP_GameResultHighlight.WBP_GameResultHighlight_C", short = "WBP_GameResultHighlight_C", objects = {} },
    { class = "/Game/Blueprints/MiniLobby/MiniLobbyPawn.MiniLobbyPawn_C", short = "MiniLobbyPawn_C", objects = {} },
}
local function lobbyObjects(index)
    local entry = lobbyTracked[index]
    if not entry.registered and loadedClass(entry.class) then
        entry.registered = true
        NotifyOnNewObject(entry.class, function(object) track(entry.objects, object) end)
        for _, object in pairs(FindAllOf(entry.short) or {}) do track(entry.objects, object) end
    end
    return prune(entry.objects)
end
local function describeMesh(actor, property)
    local ok, mesh = pcall(function()
        return actor[property]
    end)
    if not ok or not mesh or not mesh:IsValid() then
        log(property .. "=missing or unreadable: " .. tostring(mesh))
        return
    end
    log(property .. "=" .. mesh:GetFullName())
    local fields = {
        { "SkeletalMesh", function() return describeObject(mesh.SkeletalMesh) end },
        { "AnimClass", function() return describeObject(mesh.AnimClass) end },
        { "AnimInstance", function() return describeObject(mesh:GetAnimInstance()) end },
        { "AnimationMode", function() return tostring(mesh.AnimationMode) end },
        { "Visible", function() return tostring(mesh.bVisible) end },
        { "HiddenInGame", function() return tostring(mesh.bHiddenInGame) end },
        { "ActiveMontage", function()
            local anim = mesh:GetAnimInstance()
            return anim and anim:IsValid() and describeObject(anim:GetCurrentActiveMontage()) or "missing"
        end },
    }
    if property == "FPPSM" then
        for _, field in ipairs({ "AttackBool", "TypeAttack", "IsAttack", "Attack" }) do
            table.insert(fields, { "AnimInstance." .. field, function()
                return readValue(mesh:GetAnimInstance(), field)
            end })
        end
    end
    for _, field in ipairs(fields) do
        local fieldOk, result = pcall(field[2])
        log(property .. "." .. field[1] .. "=" .. (fieldOk and result or ("read error: " .. tostring(result))))
    end
end
-- Deep view diagnostic: which killer components are actually rendered, which
-- camera is in use, and whether first-person bones move during an attack.
local function shortName(obj)
    if not obj or not obj:IsValid() then return "none" end
    return (obj:GetFullName():match("([^%.:]+)$")) or obj:GetFullName()
end
local function vecText(v)
    if not v then return "nil" end
    return string.format("%.1f,%.1f,%.1f", v.X, v.Y, v.Z)
end
local function try(label, fn)
    local ok, value = pcall(fn)
    return label .. "=" .. (ok and tostring(value) or "err")
end
local diagComponents = { "FPPCamera", "FollowCamera", "ATPCCamera", "SpringArm", "FPMeshPlace", "FPPSM",
    "ChainsawFPPMesh", "Mesh", "KillerHead", "SceneCaptureComponent2D" }
local function logBones(actor, tag)
    local mesh = readObject(actor, "FPPSM")
    if not mesh then log("Bones [" .. tag .. "] FPPSM missing"); return end
    local ok, err = pcall(function()
        local count = mesh:GetNumBones()
        local origin = mesh:K2_GetComponentLocation()
        local parts = { "count=" .. tostring(count) }
        for _, index in ipairs({ math.floor(count / 3), math.floor(count * 2 / 3), count - 1 }) do
            local bone = mesh:GetBoneName(index)
            local p = mesh:GetSocketLocation(bone)
            parts[#parts + 1] = bone:ToString() .. "=" .. vecText({ X = p.X - origin.X, Y = p.Y - origin.Y, Z = p.Z - origin.Z })
        end
        parts[#parts + 1] = try("mode", function() return mesh.AnimationMode end)
        parts[#parts + 1] = try("clipPos", function() return mesh:GetPosition() end)
        parts[#parts + 1] = try("rendered", function() return mesh:WasRecentlyRendered(0.2) end)
        log("Bones [" .. tag .. "] " .. table.concat(parts, " "))
    end)
    if not ok then log("Bones [" .. tag .. "] error: " .. tostring(err)) end
end
local function deepDiag(tag)
    local actor = localKiller()
    if not actor then log("Deep diag [" .. tag .. "] no local killer"); return end
    log("Deep diag [" .. tag .. "] actor=" .. actor:GetFullName()
        .. " " .. try("actorTick", function() return actor:IsActorTickEnabled() end)
        .. " " .. try("dilation", function() return actor.CustomTimeDilation end)
        .. " " .. try("hidden", function() return actor.bHidden end))
    local pc = readObject(actor, "Controller")
    local camera = readObject(pc, "PlayerCameraManager")
    if camera then
        log("Deep diag camera " .. try("viewTarget", function() return shortName(camera:GetViewTarget()) end)
            .. " " .. try("loc", function() return vecText(camera:GetCameraLocation()) end)
            .. " " .. try("fov", function() return camera:GetFOVAngle() end))
    else
        log("Deep diag camera manager missing")
    end
    for _, name in ipairs(diagComponents) do
        local c = readObject(actor, name)
        local okComponent, errComponent = pcall(function()
        if c then
            local parts = { name .. " class=" .. (c:GetFullName():match("^(%S+)") or "?") }
            parts[#parts + 1] = try("visible", function() return c:IsVisible() end)
            parts[#parts + 1] = try("hiddenInGame", function() return c.bHiddenInGame end)
            parts[#parts + 1] = try("active", function() return c:IsActive() end)
            parts[#parts + 1] = try("tick", function() return c:IsComponentTickEnabled() end)
            parts[#parts + 1] = try("parent", function() return shortName(c:GetAttachParent()) end)
            parts[#parts + 1] = try("socket", function() return c:GetAttachSocketName():ToString() end)
            parts[#parts + 1] = try("loc", function() return vecText(c:K2_GetComponentLocation()) end)
            parts[#parts + 1] = try("rendered", function() return c:WasRecentlyRendered(0.2) end)
            for _, field in ipairs({ "bOwnerNoSee", "bOnlyOwnerSee", "GlobalAnimRateScale",
                "bEnableUpdateRateOptimizations", "MasterPoseComponent", "FieldOfView",
                "bCaptureEveryFrame", "bCaptureOnMovement", "TextureTarget", "PrimitiveRenderMode" }) do
                local value = readValue(c, field)
                if value ~= "unreadable" and value ~= "nil" then parts[#parts + 1] = field .. "=" .. value end
            end
            parts[#parts + 1] = try("skMesh", function() return shortName(c.SkeletalMesh) end)
            parts[#parts + 1] = try("anim", function() return shortName(c:GetAnimInstance()) end)
            log("Deep diag " .. table.concat(parts, " "))
        else
            log("Deep diag " .. name .. " missing")
        end
        end)
        if not okComponent then log("Deep diag " .. name .. " error: " .. tostring(errComponent)) end
    end
    logBones(actor, tag)
end
local function snapshot()
    log("Status snapshot begin")
    log("LAN role=" .. tostring(lanRole))
    local pc = localController()
    log("Local player controller=" .. describeObject(pc))
    if pc then
        local pawn = readObject(pc, "Pawn")
        log("Controller pawn=" .. describeObject(pawn))
        local state = readObject(pc, "PlayerState")
        log("PlayerState=" .. describeObject(state))
        if state then
            local ok, name = pcall(function() return state:GetPlayerName() end)
            log("PlayerState name=" .. (ok and tostring(name) or "unreadable"))
            for _, property in ipairs({ "IsKiller", "KillerType", "KillerChar", "SkinID", "NamePS", "NickNamePS" }) do
                log("PlayerState." .. property .. "=" .. readValue(state, property))
            end
        end
    end
    local actor = localKiller()
    if actor and actor:IsValid() then
        log("Local killer=" .. actor:GetFullName())
        for _, property in ipairs({ "AttackBoolAnim", "AttackAllow", "Atack?", "HandAttack" }) do
            log("Killer." .. property .. "=" .. readValue(actor, property))
        end
        describeMesh(actor, "FPPSM")
        if actor:GetFullName():find("Rabbit_C", 1, true) then
            describeMesh(actor, "ChainsawFPPMesh")
        end
        deepDiag("status")
    else
        log("No locally controlled killer actor found")
    end
    local lobbyCount = 0
    for _, model in pairs(FindAllOf("LobbyPlayerMesh_C") or {}) do
        if model:IsValid() and model:GetFullName():find("PersistentLevel", 1, true) then
            lobbyCount = lobbyCount + 1
            if lobbyCount <= 8 then
                log("Lobby model=" .. model:GetFullName())
                local player = readObject(model, "Player")
                log("Lobby model.Player=" .. describeObject(player))
                if player then
                    log("Lobby model.Player.IsKiller=" .. readValue(player, "IsKiller"))
                    log("Lobby model.Player.KillerType=" .. readValue(player, "KillerType"))
                    log("Lobby model.Player.KillerChar=" .. readValue(player, "KillerChar"))
                end
                log("Lobby model.Character=" .. readValue(model, "Character"))
                log("Lobby model.Surv?=" .. readValue(model, "Surv?"))
                log("Lobby model.SkinID=" .. readValue(model, "SkinID"))
                describeMesh(model, "MainChar")
            end
        end
    end
    log("Lobby model count=" .. tostring(lobbyCount))
    log("Status snapshot end")
end
local failedLoads = {}
local function findOrLoad(path)
    local object = StaticFindObject(path)
    if object and object:IsValid() then return object end
    if failedLoads[path] then return nil end  -- synchronous loads are tried once
    local ok, loaded = pcall(LoadAsset, path)
    if ok and loaded and loaded:IsValid() then return loaded end
    failedLoads[path] = true
end
local function restoreLobbyKillers()
    for _, model in ipairs(lobbyObjects(1)) do
        if model:IsValid() then
            local name = model:GetFullName()
            if name:find("PersistentLevel", 1, true)
                and name:find("LobbyPlayerMesh_C ", 1, true) then
                local player = readObject(model, "Player")
                local mesh = readObject(model, "MainChar")
                if player and mesh and player.IsKiller then
                    local selected = tonumber(player.KillerChar)
                    local look = lobbyKillerLooks[selected]
                    if look then
                        local currentMesh = readObject(mesh, "SkeletalMesh")
                        local currentAnim = readObject(mesh, "AnimClass")
                        local changeMesh = not currentMesh or currentMesh:GetFullName():find(look[2], 1, true) == nil
                        local changeAnim = not currentAnim or currentAnim:GetFullName():find(look[3], 1, true) == nil
                        if changeMesh or changeAnim then
                            -- The current maps keep these lobby assets loaded; maps
                            -- restored from older builds do not, so load them here
                            -- (hiding the mannequin until they appeared kept it
                            -- invisible there for good).
                            local expectedMesh = findOrLoad(look[2])
                            local expectedAnim = findOrLoad(look[3])
                            if not (expectedMesh and expectedAnim) then
                                if reportedLobbyRepair[name] ~= "missing" .. tostring(selected) then
                                    reportedLobbyRepair[name] = "missing" .. tostring(selected)
                                    log("Lobby look for " .. look[1] .. " could not be loaded: mesh="
                                        .. tostring(expectedMesh ~= nil) .. " anim=" .. tostring(expectedAnim ~= nil))
                                end
                            else
                                if changeMesh then mesh:SetSkeletalMesh(expectedMesh, true) end
                                if changeAnim then mesh:SetAnimClass(expectedAnim) end
                                pcall(function() mesh:SetVisibility(true, false) end)
                                if reportedLobbyRepair[name] ~= selected then
                                    reportedLobbyRepair[name] = selected
                                    log("Restored lobby look for " .. look[1] .. ": " .. describeObject(readObject(mesh, "SkeletalMesh"))
                                        .. ", anim=" .. describeObject(readObject(mesh, "AnimClass")))
                                end
                            end
                        end
                    end
                end
            end
        end
    end
end
local function maintainLanSession()
    if lanRole == "client" and not inMatch() then
        for _, lobby in ipairs(lobbyObjects(2)) do
            if lobby:IsValid() then
            -- only the host can start: hide the Start button (its SizeBox, as the
            -- widget itself does when starting is not possible) for the others
            local button = lobby.ButtonStart
            if button and button:IsValid() and button:GetIsEnabled() then
                button:SetIsEnabled(false)
            end
            local box = lobby.SizeBox_Start
            if box and box:IsValid() and box:GetVisibility() ~= 2 then
                box:SetVisibility(2)  -- ESlateVisibility::Hidden
                if blockedLobby ~= lobby:GetFullName() then
                    blockedLobby = lobby:GetFullName()
                    log("Client start button hidden; only the host can start")
                end
            end
            end
        end
    end
    local actor = localKiller()
    if not actor then return end
    local actorName = actor:GetFullName()
    -- KillerMasterBP's BeginPlay runs DeactivateFPPOnNotLocal, which calls
    -- FPPSM:Deactivate() when IsLocallyControlled() is false. On a listen-server
    -- host the pawn begins play before it is possessed, so the local killer's
    -- first-person mesh is switched off for good: still drawn, but no longer
    -- ticked, which freezes every first-person animation (attacks included).
    local fpMesh = readObject(actor, "FPPSM")
    if fpMesh then
        local ok, active = pcall(function() return fpMesh:IsActive() end)
        if ok and not active then
            fpMesh:Activate(false)
            log("Reactivated first-person mesh after spawn-time deactivation: active="
                .. tostring(fpMesh:IsActive()) .. " tick=" .. tostring(fpMesh:IsComponentTickEnabled()))
        end
        -- The first-person anim blueprints cache IsLocallyControlled() once in
        -- BlueprintBeginPlay (GoodCheck for Granny/Vampire/Clown/Possum/Samurai/
        -- Impostor, Validator for Rabbit/Sheet) and BlueprintUpdateAnimation does
        -- nothing while it is false. Same spawn-before-possession race as above, so
        -- the anim never copies AttackBoolAnim and the attack state never plays.
        local inst = fpMesh:GetAnimInstance()
        if inst and inst:IsValid() then
            for _, gate in ipairs({ "GoodCheck", "Validator" }) do
                local gok, value = pcall(function() return inst[gate] end)
                if gok and value == false then
                    inst[gate] = true
                    log("Enabled first-person animation update: " .. shortName(inst) .. "." .. gate .. "=" .. tostring(inst[gate]))
                end
            end
        end
    end
    if observedKiller ~= actorName then
        observedKiller = actorName
        observedKillerAt = pollCount
        checkedKiller = nil
        log("Local killer detected: " .. actorName)
    end
    if checkedKiller == actorName or pollCount - observedKillerAt < 2 then return end
    local mesh = readObject(actor, "FPPSM")
    if not mesh or not mesh:IsValid() then return end
    if not readObject(mesh, "SkeletalMesh") then return end
    local animClass = readObject(mesh, "AnimClass")
    local anim = mesh:GetAnimInstance()
    if animClass and anim and anim:IsValid() then
        checkedKiller = actorName
        log("Killer first-person animation initialized: " .. describeObject(animClass))
    else
        local className = actorName:match("^(%S+)")
        local expectedPath = firstPersonAnimClasses[className]
        if not expectedPath then
            checkedKiller = actorName
            log("No verified first-person animation fallback for " .. tostring(className))
            return
        end
        local expected = StaticFindObject(expectedPath)
        if expected and expected:IsValid() then
            mesh:SetAnimClass(expected)
            checkedKiller = actorName
            log("Restored missing first-person animation class for " .. className .. ": " .. describeObject(mesh:GetAnimInstance()))
        else
            log("First-person animation class is not loaded for " .. className)
        end
    end
end
local function executeCommand(text)
    local pc = localController()
    if not pc then log("Player controller not ready"); return end
    local system = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
    if not system:IsValid() then log("KismetSystemLibrary unavailable"); return end
    log("Executing " .. text)
    system:ExecuteConsoleCommand(pc, text, pc)
end
local function safeLanAddress(address)
    local a, b, c, d = address:match("^(%d+)%.(%d+)%.(%d+)%.(%d+)$")
    if not a then return false end
    a, b, c, d = tonumber(a), tonumber(b), tonumber(c), tonumber(d)
    if a > 255 or b > 255 or c > 255 or d > 255 then return false end
    return a == 10 or a == 127 or (a == 192 and b == 168) or (a == 172 and b >= 16 and b <= 31)
end
-- Hosting from the game's own menu: Play > Custom Game > Create Game shows
-- W_BrowserCreateServer with the map selector (rows of DT_LevelsReverse whose
-- GameMode is 2). Start Game asks the shut-down backend for a server: through
-- PC_MainMenu.BP_PC_MenuPlayfabCustomGames, which first stores the map name in
-- CS_Map, or (non-PlayFab path) PC_MainMenu.CreateServerV4, which sets
-- IsCreatingServer. Both are polled while in the main menu and the map is then
-- opened as a LAN listen server. (A native hook on the button's PlayEvent2D
-- sound froze the game at startup with UE4SS 3.0.1, so no hooks are used.)
local hostMaps = {
    BigAbbey = "/Game/Maps/GeneralLevels/Horror_Abbey/Big_Abbey/Big_Abbey_Main",
    BigFarm = "/Game/Maps/GeneralLevels/Reborn_Farm/newBigFarm/BigNew_Farm_Main",
    BigCircus = "/Game/Maps/GeneralLevels/PN_Circus/new__big_circus/NewBigCircus_Small_Main",
    SnowMain = "/Game/Maps/GeneralLevels/Reborn_Christmas/New_Fntasticvile/NewSnow_Main",
    BigEgypt = "/Game/Maps/GeneralLevels/Reborn_Store/big_egypt/BigStore_Main",
    SummerCampMRG = "/Game/Maps/GeneralLevels/Reborn_Bigcamp/PN_SummerBigCamp_Arena_Main_MRG",
    YagaMap = "/Game/Maps/GeneralLevels/Reborn_Yaga/Yaga_MAIN_",
    Kitchen = "/Game/Maps/GeneralLevels/Reborn_kitchen/NewCastle_Main",
    -- Maps restored by the Propnight-WindowsNoEditor_RevivalMaps_P.pak mod pak,
    -- which also lists them in the selector (DT_LevelsReverse GameMode set to 2).
    -- From the October 2022 build (v4.0.0). Its Small Abbey is not listed: the
    -- current Big Abbey is used instead.
    MansionReborn = "/Game/Maps/GeneralLevels/Reborn_Mansion/Reborn_Mansion_MAIN",
    CampArena = "/Game/Maps/GeneralLevels/PN_SummerCamp_VER2/Camp_Arena/PN_SummerCamp_Arena_Main",
    -- From the February 2022 build (v2.0.1), without event decorations; the farm
    -- is the daytime version.
    Farm = "/Game/Maps/GeneralLevels/PropNight_Map_TEST3_Farm_Day_MERGED",
    School = "/Game/Maps/GeneralLevels/PropNight_Map_TEST5_School",
}
local function readString(parent, field)
    if not parent or not parent:IsValid() then return nil end
    local ok, value = pcall(function() return parent[field]:ToString() end)
    if ok then return value end
end
local function selectedHostMap()
    -- One-off lookup, only after Start Game was pressed.
    for _, page in pairs(FindAllOf("W_BrowserCreateServer_C") or {}) do
        local entry = readObject(readObject(page, "WBP_MapSelector"), "CurrentLevelEntry")
        if entry then
            local ok, name = pcall(function()
                return entry.LevelData["MapName_3_58A3D1D1495CF29FC8E7FC8D19581C86"]:ToString()
            end)
            if ok and name ~= "" then return name end
        end
    end
end
-- Online mode (revival servers). Enabled by Mods/PropnightLocalMap/online.txt
-- (key=value lines: api=..., playfab=...); without it everything stays LAN.
local win64 = source:match("^(.*)/Mods/")
local online = nil
do
    local file = io.open(win64 .. "/Mods/PropnightLocalMap/online.txt", "r")
    if file then
        online = {}
        for line in file:lines() do
            local key, value = line:match("^%s*([%w_]+)%s*=%s*(%S+)")
            if key then online[key] = value end
        end
        file:close()
        log("Online mode: api=" .. tostring(online.api) .. " playfab=" .. tostring(online.playfab))
    end
end
-- Classic maps (optional, launcher DLC tab): Propnight-WindowsNoEditor_RevivalMaps_P.pak.
-- Without them the game asks the revival servers through a "/nodlc" path prefix (PlayFab
-- URL and server-list URL), so the server list and quick play leave classic map games out.
local classicMaps = false
do
    local pak = io.open(win64 .. "/../../Content/Paks/Propnight-WindowsNoEditor_RevivalMaps_P.pak", "rb")
    if pak then classicMaps = true; pak:close() end
    log("Classic maps: " .. (classicMaps and "installed" or "not installed (classic map games hidden)"))
end
local listUrlSet = {}
local function serverListWithoutClassicMaps(component)
    if classicMaps or not component then return end
    local key = tostring(component:GetAddress())
    if listUrlSet[key] then return end
    listUrlSet[key] = true
    local url = readString(component, "URL_Prod_ListServers") or ""
    if url:find("/prod/getservers", 1, true) and not url:find("/nodlc/", 1, true) then
        local ok = pcall(function() component.URL_Prod_ListServers = url:gsub("/prod/getservers", "/nodlc/prod/getservers") end)
        log("Server list without classic maps: " .. tostring(ok))
    end
end
-- The game's message box (WBP_ServerMessage: text and OK, which closes it).
local messageBoxes = {}
local function messageBox(text, seconds)
    local pc = localController()
    if not pc then return end
    local path = "/Game/UI/InGameUI/WBP_ServerMessage.WBP_ServerMessage_C"
    local cls = StaticFindObject(path)
    if not (cls and cls:IsValid()) then pcall(LoadAsset, "/Game/UI/InGameUI/WBP_ServerMessage"); cls = StaticFindObject(path) end
    if not (cls and cls:IsValid()) then log("Message box class not found"); return end
    local widget = StaticFindObject("/Script/UMG.Default__WidgetBlueprintLibrary"):Create(pc, cls, pc)
    widget:WithMessage(FText(text))
    -- the label is sized for one short line: wrap long text, keep it off the frame's edges
    pcall(function() widget.Text_Label:SetAutoWrapText(true) end)
    pcall(function() widget.Text_Label.Slot:SetPadding({ Left = 36.0, Top = 24.0, Right = 36.0, Bottom = 24.0 }) end)
    widget:AddToViewport(1000)
    -- closed by itself after a while: in a match there is no mouse cursor to press OK
    messageBoxes[#messageBoxes + 1] = { widget = widget, closeAt = os.clock() + (seconds or 30) }
    return widget
end
local function closeMessageBoxes(all)
    for i = #messageBoxes, 1, -1 do
        local box = messageBoxes[i]
        if all or os.clock() > box.closeAt then
            pcall(function() if box.widget:IsValid() then box.widget:RemoveFromParent() end end)
            table.remove(messageBoxes, i)
        end
    end
end
-- "missingmaps <map>": written by the launcher when the player tries to join a classic
-- map game without the Classic maps.
local function showMissingMaps(map, from)
    local where = (map and map ~= "") and (" (" .. map .. ")") or ""
    messageBox((from and (from .. " invites you to a game on a classic map") or "This game is on a classic map") .. where
        .. " that is not installed.\nInstall the Classic maps from the DLC tab of the Propnight Revival launcher, then join again.")
    log("Missing classic maps message shown" .. where)
end
-- Invites from friends (launcher): "invite <port> <classic 0/1> <players> <name>|<map>".
-- Shown in the game's two-button dialog WBP_LeaveTeamDialog, relabelled JOIN / IGNORE.
-- Its own Yes does nothing outside a Steam lobby (GetAmILobbyMember) and No hides it.
-- A click gives the (focusable) button the keyboard focus, which stays: the tick reads
-- JOIN from Button_Yes:HasKeyboardFocus() and IGNORE from the dialog being collapsed
-- (RegisterHook on the button's Blueprint event is refused by UE4SS 3.0.1). The join
-- runs in the next slow tick; the dialog goes away after 60 s.
local currentServer = nil   -- ip:port of the game joined as a client (presence file, invites)
local pendingInvite = nil
local queuedCommand = nil   -- run by slowTick (runCommand is defined after the tick functions)
local inviteKeyPressed = false
local dialogPath = "/Game/UI/SocialUI/WBP_LeaveTeamDialog.WBP_LeaveTeamDialog_C"
local function inviteDialogClass()
    local cls = StaticFindObject(dialogPath)
    if not (cls and cls:IsValid()) then pcall(LoadAsset, "/Game/UI/SocialUI/WBP_LeaveTeamDialog"); cls = StaticFindObject(dialogPath) end
    return cls and cls:IsValid() and cls or nil
end
local function findWidget(widget, name, depth)
    if not widget or (depth or 0) > 12 then return nil end
    local okName, own = pcall(function() return widget:GetFName():ToString() end)
    if okName and own == name then return widget end
    local okCount, count = pcall(function() return widget:GetChildrenCount() end)
    for i = 0, (okCount and count or 0) - 1 do
        local okChild, child = pcall(function() return widget:GetChildAt(i) end)
        local found = okChild and child and child:IsValid() and findWidget(child, name, (depth or 0) + 1)
        if found then return found end
    end
end
local function showInvite(command)
    local port, classic, players, from, map = command:match("^invite (%d+) ([01]) (%d+) ([%w_%-]+)|(.*)$")
    port = tonumber(port)
    if not port then log("Invalid invite: " .. command); return end
    if classic == "1" and not classicMaps then showMissingMaps(map, from); return end
    -- already in that game (opening it again while connected to it crashed the game)
    if currentServer and currentServer:match(":(%d+)$") == tostring(port) then
        log("Invite from " .. from .. " ignored: already in that game")
        return
    end
    closeMessageBoxes(true)
    if pendingInvite and pendingInvite.dialog then pcall(function() pendingInvite.dialog:RemoveFromParent() end) end
    pendingInvite = { port = port, expires = os.clock() + 60, from = from }
    local pc = localController()
    local ok, err = pcall(function()
        local cls = inviteDialogClass()
        if not cls then error("dialog class not found") end
        local dialog = StaticFindObject("/Script/UMG.Default__WidgetBlueprintLibrary"):Create(pc, cls, pc)
        local root = dialog.WidgetTree.RootWidget
        local label = findWidget(root, "TextBlock_37")
        if not label then error("dialog label not found") end
        label:SetText(FText(from .. " invites you to their game\n" .. (map ~= "" and map or "?") .. "  ·  " .. players .. "/5 players"))
        pcall(function() label:SetAutoWrapText(true) end)
        pcall(function() label:SetJustification(1) end)   -- centre
        dialog.TextBlock_Yes:SetText(FText("JOIN"))
        pcall(function() findWidget(root, "TextBlock_130"):SetText(FText("IGNORE")) end)
        dialog:AddToViewport(1000)
        pcall(function() dialog:ShowLeaveLobbyDialog() end)
        dialog:SetVisibility(0)
        pendingInvite.dialog = dialog
    end)
    if not ok then
        -- fallback: a plain message (join from the launcher)
        log("Invite dialog error: " .. tostring(err))
        pendingInvite = nil
        messageBox(from .. " invites you to their game: " .. (map ~= "" and map or "?") .. ", " .. players .. "/5 players.\n"
            .. "Join from the Propnight Revival launcher.", 30)
    end
    log("Invite from " .. from .. " shown (port " .. port .. ")")
end
local aliveFile = win64 .. "/revival-hosting.txt"
local function touchAliveFile()
    local file = io.open(aliveFile, "w")
    if file then file:write(tostring(os.time())); file:close() end
end
local function shellSafe(text)
    return (tostring(text or ""):gsub("[^%w _%-%.]", ""))
end
-- The players' traffic reaches this listen server through the revival relay:
-- RevivalRelay.exe registers the game (listed in the in-game server browser)
-- and tunnels the relay to 127.0.0.1:7777; the host's IP is never shown.
local function startRelayAgent(mapName)
    local name = ""
    local ok, value = pcall(function() return localController().PlayerState:GetPlayerName():ToString() end)
    if ok and value then name = shellSafe(value) end
    if name:match("^%s*$") then name = "Propnight" end
    local api = tostring(online.api or ""):gsub('[^%w:/%._%-]', "")
    touchAliveFile()
    local exe = (win64 .. "/RevivalRelay/RevivalRelay.exe"):gsub("/", "\\")
    local alive = aliveFile:gsub("/", "\\")
    -- the account's Steam ID (written by the launcher for the Steam emulator) tells
    -- the server whose game this is: friends see it and can be invited to it
    local steamId = ""
    local idFile = io.open(win64 .. "/../../../Engine/Binaries/ThirdParty/Steamworks/Steamv147/Win64/steam_settings/force_steamid.txt", "r")
    if idFile then
        steamId = (idFile:read("*l") or ""):match("^%s*(%d+)%s*$") or ""
        idFile:close()
    end
    local command = string.format('start "" "%s" --api %s --name "%s" --map %s --alive-file "%s"%s',
        exe, api, name, shellSafe(mapName), alive, steamId ~= "" and (" --steam " .. steamId) or "")
    log("Starting relay agent for " .. name .. " on " .. shellSafe(mapName))
    -- Off the game thread: the first launch of the exe can take seconds.
    ExecuteWithDelay(10, function() os.execute(command) end)
end
-- The menu's PlayFab component calls setPlayFabSettings(…, "https://23b52.playfabapi.com/")
-- in BeginPlay; the same call is made again with the revival URL afterwards.
local playfabApplied = {}
local function applyOnlinePlayfab(pc)
    if not online or not online.playfab or not pc or not pc:IsValid() then return end
    local key = pc:GetFullName() .. "@" .. tostring(pc:GetAddress())
    if playfabApplied[key] then return end
    local utilities = StaticFindObject("/Script/PlayFab.Default__PlayFabUtilities")
    if not utilities or not utilities:IsValid() then return end
    local url = online.playfab .. (classicMaps and "" or ((online.playfab:sub(-1) == "/" and "" or "/") .. "nodlc/"))
    local ok, err = pcall(function() utilities:setPlayFabSettings("23B52", "", url, "", "", "") end)
    playfabApplied[key] = true
    log("PlayFab URL set to " .. url .. ": " .. (ok and "ok" or tostring(err)))
end
if online then
    NotifyOnNewObject("/Script/Engine.PlayerController", function(pc)
        for _, delay in ipairs({ 500, 2000 }) do
            ExecuteWithDelay(delay, function()
                ExecuteInGameThread(function() pcall(applyOnlinePlayfab, pc) end)
            end)
        end
    end)
end
local function hostFromMenu(mapName)
    local path = mapName and hostMaps[mapName]
    if not path then
        log("Create game: unknown or missing map selection (" .. tostring(mapName) .. "), using BigAbbey")
        mapName, path = "BigAbbey", hostMaps.BigAbbey
    end
    lanRole = "host"
    log("Create game from menu: " .. mapName .. " -> " .. path)
    if online then
        local ok, err = pcall(startRelayAgent, mapName)
        if not ok then log("Relay agent error: " .. tostring(err)) end
    end
    executeCommand("open " .. path .. "?listen?port=7777")
end
-- Players who join from the server browser travel without the mod's join
-- command: their role is read from the world once a match map is loaded.
local function detectRole()
    if lanRole then return end
    local pc = localController()
    if not pc or pc:GetFullName():find("PC_MainMenu_C", 1, true) then return end
    local system = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
    local ok, standalone = pcall(function() return system:IsStandalone(pc) end)
    if not ok or standalone then return end
    local okServer, server = pcall(function() return system:IsServer(pc) end)
    if okServer then
        lanRole = server and "host" or "client"
        log("Network role detected: " .. lanRole)
    end
end
local menuWatch = { pc = nil, baseline = nil, done = false }
local function watchMenuHost()
    local pc = localController()
    if not pc or not pc:GetFullName():find("PC_MainMenu_C", 1, true) then return false end
    local playfab = readObject(pc, "BP_PC_MenuPlayfabCustomGames")
    if online then pcall(serverListWithoutClassicMaps, playfab) end
    local csMap = readString(playfab, "CS_Map") or ""
    if menuWatch.pc ~= pc:GetFullName() then
        menuWatch.pc, menuWatch.baseline, menuWatch.done = pc:GetFullName(), csMap, false
        menuWatch.since = os.clock()
        log("Menu hosting ready: Play > Custom Game > Create Game > Start Game")
        return true
    end
    if menuWatch.done then return true end
    local creating = readValue(pc, "IsCreatingServer") == "true"
    if csMap ~= "" and csMap ~= menuWatch.baseline then
        menuWatch.done = true
        hostFromMenu(csMap)
    elseif creating then
        menuWatch.done = true
        hostFromMenu(selectedHostMap())
    end
    return true
end
-- Lobby role swap diagnostic: GS_PropHunt.SwapPlayers only swaps roles when
-- each player's LobbyPawn is the pawn stored for its slot (killer1, surv1..surv4)
-- in GS.LobbyState; this logs that state whenever it changes.
local lastSlotState = nil
local lastSlotCheck = 0
local lastRoles = nil
local function propHuntControllers()
    local list = {}
    for _, pc in ipairs(prune(controllers)) do
        if pc:GetFullName():find("PC_PropHunt_C", 1, true) then list[#list + 1] = pc end
    end
    return list
end
local function lobbySlotsDiag()
    if lanRole ~= "host" or inMatch() or os.clock() - lastSlotCheck < 2 then return end
    lastSlotCheck = os.clock()
    -- After a role swap GS_PropHunt.SwapPlayers reassigns the slots silently, so
    -- LobbyStateUpdate (which refreshes every player's lobby scene: models,
    -- avatars, slots) is never sent: send it when the roles change.
    local roles = {}
    for _, pc in ipairs(propHuntControllers()) do
        roles[#roles + 1] = tostring(pc:GetAddress()) .. "=" .. readValue(pc, "IsKiller")
    end
    table.sort(roles)
    -- swap diagnostic (written when it changes): AcceptSwap reads the accepter's
    -- PS.SwapSender (a lobby pawn), takes that pawn's controller and calls
    -- GS.SwapPlayers, which frees both slots only when GS.LobbyState holds each
    -- player's PC.LobbyPawn
    local state = {}
    for _, pc in ipairs(propHuntControllers()) do
        local ps = readObject(pc, "PlayerState")
        local lobbyPawn = readObject(pc, "LobbyPawn")
        local sender = ps and readObject(ps, "SwapSender")
        local okCtl, ctl = pcall(function() return sender and sender:GetController() end)
        local okOwn, own = pcall(function() return lobbyPawn and lobbyPawn:GetController() end)
        state[#state + 1] = string.format("%s[%s] slot=%s killer=%s/%s lobbyPawn=%s(ctl %s) pawn=%s sender=%s(ctl %s)",
            readString(ps, "NickNamePS") or "?", (pc:IsLocalController() and "local" or "remote"),
            readString(pc, "LobbySlotName") or "?", readValue(pc, "IsKiller"), readValue(ps, "IsKiller"),
            shortName(lobbyPawn), okOwn and shortName(own) or "err", shortName(readObject(pc, "Pawn")),
            shortName(sender), okCtl and shortName(ctl) or "err")
    end
    table.sort(state)
    local stateText = table.concat(state, " | ")
    if stateText ~= lastSlotState then
        lastSlotState = stateText
        local gs = FindFirstOf("GS_PropHunt_C")
        local okFree, free = pcall(function() return gs:IsKillerSlotFree() end)
        log("Swap state: " .. stateText .. " | killer slot free=" .. tostring(okFree and free))
    end
    local signature = table.concat(roles, ",")
    local previousKiller = lastRoles and lastRoles:match("([^,=]+)=true")
    local currentKiller = signature:match("([^,=]+)=true")
    if lastRoles and previousKiller and currentKiller and previousKiller ~= currentKiller then
        local gs = FindFirstOf("GS_PropHunt_C")
        local ok, err = pcall(function() gs:SendLobbyState() end)
        log("Roles swapped: lobby state resent to every player: " .. (ok and "ok" or tostring(err)))
    end
    lastRoles = signature
end
-- Lobby slots fix (host). In the lobby GS_PropHunt's Tick runs CleanSlots,
-- Assign Slots and SendLobbyState every second. CleanSlots frees every slot whose
-- player is not in GM_PropHunt.PlayfabPlayers, and Assign Slots then reserves a
-- slot again for each player (SetLobbySlotName, which also clears
-- PlayerState.SwapSender). PlayfabPlayers is filled when a player's PlayFab
-- session is confirmed (ConfirmPlayerJoined) or by PlayerJoinedNonPlayfab; revival
-- players get neither, so the slots were rebuilt every second: a killer's swap
-- request was wiped before the survivor could accept it, and swapped roles were
-- undone. Players missing from the list are registered with PlayerJoinedNonPlayfab.
-- PS_PropHunt's BeginPlay calls LoadSkinsAndBanner (which fills SkinArr and sets
-- the banner, tag and avatar) only when it has no authority. On a dedicated server
-- every player qualifies; on a listen server the host's own PlayerState never loads
-- them, and LobbyPlayerMesh.SetSkeletalSkinMesh does nothing while SkinArr is empty:
-- the host's lobby model kept its previous mesh (a killer in T-pose after a swap
-- to survivor). The host's skins are loaded once here.
local hostSkinsRequested = nil
local function loadHostSkins()
    local ps = readObject(localController(), "PlayerState")
    if not ps or not ps:GetFullName():find("PS_PropHunt_C", 1, true) then return end
    local key = ps:GetFullName()
    if hostSkinsRequested == key then return end
    local okNum, count = pcall(function() return ps.SkinArr:GetArrayNum() end)
    if okNum and count > 0 then return end
    hostSkinsRequested = key
    local ok, err = pcall(function() ps:LoadSkinsAndBanner() end)
    log("Host skins and banner loaded: " .. (ok and "ok" or tostring(err)))
    -- PS.SteamPlayerID (a random number the server gives each joining player) identifies
    -- the players in the end-of-match stats (GS.HighlightPlayerInformation); the host's
    -- own PlayerState never got one, so its stats were missing there.
    if (readString(ps, "SteamPlayerID") or "") == "" then
        local okId, errId = pcall(function() ps.SteamPlayerID = tostring(math.random(1, 200000)) end)
        log("Host stats id: " .. (okId and tostring(readString(ps, "SteamPlayerID")) or tostring(errId)))
    end
end
local registeredPlayers = {}
local lastRegister = 0
local function registerLobbyPlayers()
    if lanRole ~= "host" or inMatch() or os.clock() - lastRegister < 2 then return end
    lastRegister = os.clock()
    loadHostSkins()
    local gm = FindFirstOf("GM_PropHunt_C")
    if not gm or not gm:IsValid() then return end
    local known = {}
    pcall(function()
        gm.PlayfabPlayers:ForEach(function(_, element)
            local pc = element:get()
            if pc and pc:IsValid() then known[tostring(pc:GetAddress())] = true end
        end)
    end)
    for _, pc in ipairs(propHuntControllers()) do
        local key = pc:IsValid() and tostring(pc:GetAddress())
        if key and not known[key] and registeredPlayers[key] ~= pc:GetFullName() then
            registeredPlayers[key] = pc:GetFullName()
            local ok, err = pcall(function() gm:PlayerJoinedNonPlayfab(pc) end)
            log("Lobby player registered with the game mode: " .. shortName(pc) .. " " .. (ok and "ok" or tostring(err)))
        end
    end
end
-- Lobby player row (every player). W_MiniLobby still has the row of player slots
-- at the top of the screen (SlotsBox, W_Slot widgets: nickname, killer and ready
-- icons) but v5.4.4 never calls its CreateSlots, and UpdateLobbyState hides every
-- nickname but the killer's own for the killer: a killer could not see who was
-- waiting. The row is created here and each slot is given the lobby pawn whose
-- PlayerState holds that slot name (PS.NamePS, set for every player by
-- SetLobbySlotName), through W_Slot.Process. The row sits in the top right corner
-- (top centre is where the "game starts in" countdown and ready players appear),
-- every slot on a light square (white at 30 %, like the character buttons), an
-- empty slot showing that square and "...".
-- W_Slot.Process shows the player's character icon (DT_SurvivorNames /
-- DT_KillerNames), which told the killer which survivors were picked and the
-- other way round. The icon is hidden; an avatar (Customize > Banner, DT_CustomAvatars)
-- is only a coloured square (the face in the game's banner is the character portrait),
-- so the nickname's first letter is drawn on the plain square instead, in a TextBlock
-- added to the avatar's overlay (font size 30 rather than a render scale, which blurred it).
-- Once the host has started the countdown (ready counter shown), each nickname
-- gets a V (PS_PropHunt.Ready?) or an X and the square turns green or red.
local SLOT_WIDTH = 90.0      -- W_Slot is 152 wide (nickname box); names longer than this scroll
local SLOT_PADDING = 2.0     -- SlotsBox (UniformGridPanel) padding, 8 in the widget
local gameInstance = nil
local endScreenAt = nil   -- last end screen built (W_VictoryScreen / WBP_EndGameLevel)
local lastEndScreenAt = nil   -- same, never cleared (calibration rank hiding)
local rowSlots = {}
local rowMarks = {}
local slotInitials = {}
local initialLogged = false
local function slotInitial(slot)
    local key = tostring(slot:GetAddress())
    if slotInitials[key] ~= nil then return slotInitials[key] or nil end
    local ok, text = pcall(function()
        local t = StaticConstructObject(StaticFindObject("/Script/UMG.TextBlock"), slot.WidgetTree)
        local overlaySlot = slot.Avatar_BG:GetParent():AddChildToOverlay(t)
        overlaySlot:SetHorizontalAlignment(2)   -- centre
        overlaySlot:SetVerticalAlignment(2)
        t:SetShadowOffset({ X = 1.0, Y = 1.0 })
        t:SetShadowColorAndOpacity({ R = 0.0, G = 0.0, B = 0.0, A = 0.8 })
        t:SetVisibility(3)   -- HitTestInvisible
        return t
    end)
    -- FSlateFontInfo is a nested struct (SetFont does not pass from Lua): its Size field
    -- is written in place, then pushed to Slate
    local okFont, errFont = false, nil
    if ok and text then
        okFont, errFont = pcall(function()
            text.Font.Size = 30
            text:SynchronizeProperties()
        end)
    end
    if not initialLogged then
        initialLogged = true
        local okSize, size = pcall(function() return text.Font.Size end)
        log("Lobby player row initials: " .. (ok and "ok" or tostring(text)) .. ", font size "
            .. (okFont and tostring(okSize and size) or ("error " .. tostring(errFont))))
    end
    slotInitials[key] = ok and text and text:IsValid() and text or false
    return slotInitials[key] or nil
end
local function showInitial(slot, name)
    local text = slotInitial(slot)
    if not text then return end
    local first = (name or ""):match("^[%z\1-\127\194-\244][\128-\191]*") or ""   -- first UTF-8 character
    pcall(function() text:SetText(FText(first:upper())) end)
end
local lastRowUpdate = 0
local rowPlaced = {}
local rowStyleLogged = false
local function styleSlot(slot)
    pcall(function() slot.RetainerBox_0:SetRetainRendering(false) end)   -- no fade-out on the nickname
    pcall(function() slot.RetainerBox_0:SetEffectMaterial(nil) end)
    -- narrower columns: the root SizeBox_1 and the nickname's SizeBox_8 (not variables)
    pcall(function() slot.RetainerBox_0:GetParent():SetWidthOverride(SLOT_WIDTH) end)
    pcall(function() slot.PlayerSlotSwitcher:GetParent():GetParent():GetParent():SetWidthOverride(SLOT_WIDTH) end)
    local ok, err = pcall(function()
        slot.Avatar_BG:SetBrushResourceObject(nil)   -- no texture: a plain, sharp square
        slot.Avatar_BG:SetColorAndOpacity({ R = 1.0, G = 1.0, B = 1.0, A = 0.3 })
        slot.Avatar_BG:SetVisibility(4)   -- SelfHitTestInvisible
    end)
    if not rowStyleLogged then
        rowStyleLogged = true
        local okRes, res = pcall(function() return slot.Avatar_BG.Brush.ResourceObject end)
        log("Lobby player row style: applied=" .. tostring(ok) .. " " .. tostring(err)
            .. " now=" .. tostring(okRes and res and res:IsValid() and res:GetFullName()))
    end
end
local function showSlot(slot, pawn)
    local key = tostring(slot:GetAddress())
    pcall(function() slot:Process(pawn) end)
    rowMarks[key] = nil
    if pawn then
        pcall(function() slot.Image_CharIcon:SetVisibility(2) end)   -- character icon: hidden
        pcall(function() slot.Nickname:SetVisibility(4) end)
    else
        -- empty: the occupied page with the square and "..." (Process(nil) shows a
        -- "reserve" page with a waiting spinner)
        pcall(function() slot.PlayerSlotSwitcher:SetActiveWidgetIndex(0) end)
        pcall(function() slot.Image_CharIcon:SetVisibility(2) end)
        pcall(function() slot.Nickname:SetText(FText("...")) end)
        pcall(function() slot.Nickname:SetVisibility(4) end)
        pcall(function() slot.Avatar_BG:SetColorAndOpacity({ R = 1.0, G = 1.0, B = 1.0, A = 0.3 }) end)
        showInitial(slot, "")
    end
    pcall(function() slot:SetVisibility(4) end)
end
-- name: MiniLobbyPawn.Nickname (what W_Slot.Process shows); mark: "ready",
-- "waiting" or nil (no countdown: plain nickname, white square)
local markColors = { ready = { R = 0.1, G = 0.75, B = 0.25, A = 0.6 }, waiting = { R = 0.8, G = 0.1, B = 0.1, A = 0.5 } }
local function showMark(slot, name, mark)
    local key = tostring(slot:GetAddress())
    local state = name .. "|" .. (mark or "none")
    if rowMarks[key] == state then return end
    rowMarks[key] = state
    local text = name
    if mark == "ready" then text = name .. "  V" elseif mark == "waiting" then text = name .. "  X" end
    pcall(function() slot.Nickname:SetText(FText(text)) end)
    showInitial(slot, name)
    pcall(function() slot.Avatar_BG:SetColorAndOpacity(markColors[mark] or { R = 1.0, G = 1.0, B = 1.0, A = 0.3 }) end)
end
local function placeRow(lobby)
    local key = tostring(lobby:GetAddress())
    if rowPlaced[key] then return end
    local ok, err = pcall(function()
        local canvasSlot = lobby.WidgetSwitcher_Slots.Slot
        canvasSlot:SetMinimum({ X = 1.0, Y = 0.0 })   -- anchors (SetAnchors' nested struct does not pass from Lua)
        canvasSlot:SetMaximum({ X = 1.0, Y = 0.0 })
        canvasSlot:SetAlignment({ X = 1.0, Y = 0.0 })
        canvasSlot:SetPosition({ X = -40.0, Y = 30.0 })
    end)
    pcall(function() lobby.SlotsBox:SetSlotPadding({ Left = SLOT_PADDING, Top = 0.0, Right = SLOT_PADDING, Bottom = 0.0 }) end)
    rowPlaced[key] = true
    if not ok then log("Lobby player row placement error: " .. tostring(err)) end
    pcall(function()
        local c = lobby.WidgetSwitcher_Slots.Slot
        local a, pos, size, al = c:GetAnchors(), c:GetPosition(), c:GetSize(), c:GetAlignment()
        log(string.format("Lobby player row placed: anchors %s,%s-%s,%s pos %s,%s size %s,%s align %s,%s autosize %s", tostring(a.Minimum.X), tostring(a.Minimum.Y),
            tostring(a.Maximum.X), tostring(a.Maximum.Y), tostring(pos.X), tostring(pos.Y), tostring(size.X), tostring(size.Y), tostring(al.X), tostring(al.Y), tostring(c:GetAutoSize())))
    end)
end
local function updateLobbyRow()
    if not lanRole or inMatch() or os.clock() - lastRowUpdate < 0.5 then return end
    lastRowUpdate = os.clock()
    for _, lobby in ipairs(lobbyObjects(2)) do
        if lobby:IsValid() then
            local box = lobby.SlotsBox
            if box and box:IsValid() and box:GetChildrenCount() == 0 then
                local gs = FindFirstOf("GS_PropHunt_C")
                -- CreateSlots waits for the lobby state, which these players never confirm
                pcall(function() if gs and not gs["IsLobbyStateAccepted?"] then gs["IsLobbyStateAccepted?"] = true end end)
                local ok, err = pcall(function() lobby:CreateSlots() end)
                if not ok then log("Lobby player row error: " .. tostring(err))
                elseif box:GetChildrenCount() > 0 then log("Lobby player row created: " .. box:GetChildrenCount() .. " slots") end
                rowSlots = {}
            end
            if box and box:IsValid() and box:GetChildrenCount() > 0 then placeRow(lobby) end
            local pawns = {}
            for _, pawn in ipairs(lobbyObjects(6)) do
                if pawn:GetFullName():find("PersistentLevel", 1, true) then
                    local slotName = readString(readObject(pawn, "PlayerState"), "NamePS")
                    if slotName and slotName ~= "" then pawns[slotName] = pawn end
                end
            end
            -- the host started the countdown: the ready counter ("1/5") is shown
            local okCounter, counter = pcall(function() return lobby.HorizontalBox_ReadyCounter:GetVisibility() end)
            local countdown = okCounter and counter == 0
            for i = 0, (box and box:IsValid() and box:GetChildrenCount() or 0) - 1 do
                local slot = box:GetChildAt(i)
                local slotName = slot and slot:IsValid() and readString(slot, "Name")
                if slotName then
                    local pawn = pawns[slotName]
                    local key = tostring(slot:GetAddress())
                    local current = pawn and tostring(pawn:GetAddress()) or "empty"
                    if rowSlots[key] ~= current then
                        if not rowSlots[key] then styleSlot(slot) end
                        rowSlots[key] = current
                        showSlot(slot, pawn)
                    end
                    local ps = pawn and readObject(pawn, "PlayerState")
                    if ps then
                        local mark = nil
                        if countdown then mark = readValue(ps, "Ready?") == "true" and "ready" or "waiting" end
                        showMark(slot, readString(pawn, "Nickname") or "", mark)
                    end
                end
            end
        end
    end
end
-- In-game reports (Tab > player > Report). The game only relays them to the
-- reported player's own PC (BP_BanManager.ReportMulti). After a report the window
-- switches WidgetSwitcher_1 to its "report sent" page (index 1); the reason is the
-- button the cursor was on. The report is appended to revival-reports.jsonl, which
-- the launcher sends to the revival server with the player's account.
local reportsFile = win64 .. "/revival-reports.jsonl"
local reportWindows = {}
local reportReasons = { { "Button_ReportCheating", "cheating" }, { "Button_ReportToxic", "toxic" }, { "Button_ReportTeaming", "teaming" } }
local function jsonString(text)
    local escaped = tostring(text or ""):gsub('[%c"\\]', function(c) return string.format("\\u%04x", c:byte()) end)
    return '"' .. escaped .. '"'
end
local function watchReports()
    for _, window in ipairs(lobbyObjects(3)) do
        local key = window:GetFullName() .. "@" .. tostring(window:GetAddress())
        local ps = readObject(window, "PlayerStateRef")
        local ref = ps and tostring(ps:GetAddress()) or nil
        local state = reportWindows[key]
        if not state or state.ref ~= ref then
            state = { ref = ref }
            reportWindows[key] = state
        end
        local okPage, pageIndex = pcall(function() return window.WidgetSwitcher_1:GetActiveWidgetIndex() end)
        if ps and okPage then
            if pageIndex == 0 then
                for _, entry in ipairs(reportReasons) do
                    local ok, hovered = pcall(function() return window[entry[1]]:IsHovered() end)
                    if ok and hovered then state.hover = entry[2] end
                end
            elseif pageIndex == 1 and state.page == 0 then
                local reason = state.hover or "cheating"
                local name = readString(ps, "NickNamePS")
                if not name or name == "" then
                    local okName, value = pcall(function() return ps:GetPlayerName():ToString() end)
                    name = okName and value or "?"
                end
                local map = (localController() and localController():GetWorld():GetFullName():match("([%w_]+):PersistentLevel")) or ""
                local file = io.open(reportsFile, "a")
                if file then
                    file:write(string.format('{"reported":%s,"reason":%s,"map":%s,"time":%d}\n', jsonString(name), jsonString(reason), jsonString(map), os.time()))
                    file:close()
                end
                log("Report recorded: " .. name .. " for " .. reason)
            end
            state.page = pageIndex
        end
    end
end
-- End-of-match screens of a player still in calibration (GI.MatchesPlayed <=
-- GI."Matches to Calibrate", the menu's rule in WBP_PlayerRank): the rank scroller of
-- WBP_LevelProgress and the rank icon of the result cards show a rank only when the
-- game is a matchmaking one, without looking at calibration. They are hidden.
local function hideCalibrationRank()
    if not lastEndScreenAt or os.clock() - lastEndScreenAt > 180 then return end
    local gi = gameInstance
    if not (gi and gi:IsValid()) then return end
    local okP, played = pcall(function() return gi.MatchesPlayed end)
    local okC, needed = pcall(function() return gi["Matches to Calibrate"] end)
    if not (okP and okC and tonumber(played) and tonumber(needed)) or played > needed then return end
    for _, progress in ipairs(lobbyObjects(4)) do
        pcall(function()
            if progress.WBP_PlayerRankScroller:GetVisibility() ~= 1 then progress.WBP_PlayerRankScroller:SetVisibility(1) end
        end)
    end
    for _, card in ipairs(lobbyObjects(5)) do
        pcall(function()
            if card.Image_CollapsedRankIcon:GetVisibility() ~= 1 then card.Image_CollapsedRankIcon:SetVisibility(1) end
        end)
    end
end
-- Dropping a carried survivor as the listen-server host killer. The right-click handler
-- (KillerMasterBP, local) sets Stunned? then calls DropServ, and DropServ only drops
-- (DropMulti) when Stunned? is false: on a dedicated server DropServ runs on the server's
-- copy of the killer, where the local flag is not set, so the drop happens; on the host it
-- is the same object, DropServ only unlocks the input and the survivor stays on the
-- killer's back (the client still carried, the host back in first person, unable to act).
-- The host's mod finishes the drop: killer still holding an attached survivor, Stunned?
-- set, no chair move, no flashlight, no drop running -> DropMulti (multicast from the server).
local hostDropSeen = nil
local function finishHostDrop()
    if lanRole ~= "host" then return end
    local killer = localKiller()
    if not killer then hostDropSeen = nil; return end
    local grabbed = readObject(killer, "GrabbedChar")
    local stuck = grabbed and readValue(killer, "IsHolded") == "true" and readValue(killer, "Stunned?") == "true"
        and readValue(killer, "ToChairMove") ~= "true" and readValue(killer, "ChairDrop") ~= "true"
        and readValue(killer, "Flashed") ~= "true" and readValue(killer, "SimpleDrop") ~= "true"
    if stuck then
        local okP, parent = pcall(function() return grabbed:GetAttachParentActor() end)
        stuck = okP and parent and parent:IsValid() and parent:GetAddress() == killer:GetAddress()
    end
    if not stuck then hostDropSeen = nil; return end
    -- seen on two ticks in a row: not a short stun while carrying
    if not hostDropSeen then hostDropSeen = os.clock(); return end
    hostDropSeen = nil
    local ok, err = pcall(function() killer:DropMulti() end)
    log("Host killer drop finished (DropMulti): " .. (ok and "ok" or tostring(err)))
end
local function fastTick()
    local okDrop, errDrop = pcall(finishHostDrop)
    if not okDrop then log("Host drop error: " .. tostring(errDrop)) end
    closeMessageBoxes(false)
    if pendingInvite and pendingInvite.dialog then
        local dialog = pendingInvite.dialog
        local okYes, yes = pcall(function() return dialog.Button_Yes:HasKeyboardFocus() end)
        local okVis, vis = pcall(function() return dialog:GetVisibility() end)
        if okYes and yes then
            inviteKeyPressed = true
        elseif not okVis or vis == 1 or not dialog:IsValid() then
            log("Invite from " .. pendingInvite.from .. " ignored")
            pcall(function() dialog:RemoveFromParent() end)
            pendingInvite = nil
        end
    end
    if inviteKeyPressed then
        inviteKeyPressed = false
        if pendingInvite and os.clock() < pendingInvite.expires then
            local invite = pendingInvite
            pendingInvite = nil
            closeMessageBoxes(true)
            if invite.dialog then pcall(function() invite.dialog:RemoveFromParent() end) end
            log("Invite from " .. invite.from .. " accepted")
            queuedCommand = "joinrelay " .. invite.port
        end
    elseif pendingInvite and os.clock() > pendingInvite.expires then
        if pendingInvite.dialog then pcall(function() pendingInvite.dialog:RemoveFromParent() end) end
        pendingInvite = nil
    end
    local okRank, errRank = pcall(hideCalibrationRank)
    if not okRank then log("Calibration rank error: " .. tostring(errRank)) end
    if lanRole then
        local ok, err = pcall(lobbySlotsDiag)
        if not ok then log("Lobby slots diagnostic error: " .. tostring(err)) end
        local okReports, errReports = pcall(watchReports)
        if not okReports then log("Report watch error: " .. tostring(errReports)) end
        local okSlots, errSlots = pcall(registerLobbyPlayers)
        if not okSlots then log("Lobby player registration error: " .. tostring(errSlots)) end
        local okRow, errRow = pcall(updateLobbyRow)
        if not okRow then log("Lobby player row error: " .. tostring(errRow)) end
        local okRestore, errRestore = pcall(function()
            if not inMatch() then restoreLobbyKillers() end
        end)
        if not okRestore then log("Lobby restore error: " .. tostring(errRestore)) end
    end
    local ok, err = pcall(watchMenuHost)
    if not ok then log("Menu hosting error: " .. tostring(err)) end
end
-- Several maps keep their Halloween decorations in a separate sublevel that the
-- level blueprint always streams in (Big_Abbey_Halloween: candles and ceiling
-- garlands; the restored v4 Farm, Mansion, Camp and Small Abbey have their own
-- *_Halloween sublevels). Hiding it gives the base map back. The level
-- blueprints load their sublevels as a chain, so it is removed only once every
-- sublevel has loaded.
local cleanedWorld = nil
local function removeHalloweenSublevels()
    local world = localController() and localController():GetWorld()
    if not world or not world:IsValid() then return end
    local worldId = world:GetFullName() .. "@" .. tostring(world:GetAddress())
    if cleanedWorld == worldId then return end
    local levels, removed = {}, {}
    world.StreamingLevels:ForEach(function(_, element)
        local streaming = element:get()
        if streaming and streaming:IsValid() then levels[#levels + 1] = streaming end
    end)
    for _, streaming in ipairs(levels) do
        local loaded = streaming:GetLoadedLevel()
        if not loaded or not loaded:IsValid() then return end
    end
    for _, streaming in ipairs(levels) do
        local name = streaming:GetLoadedLevel():GetFullName()
        if name:find("_Halloween", 1, true) then
            streaming:SetShouldBeVisible(false)
            streaming:SetShouldBeLoaded(false)
            removed[#removed + 1] = name:match("([%w_]+):PersistentLevel") or name
        end
    end
    -- The February 2022 day farm keeps a Stationary sun whose baked shadow maps
    -- include the props of that build, so a destroyed prop left its shadow on the
    -- ground. A Movable sun ignores the baked shadows and shadows dynamically.
    if worldId:find("PropNight_Map_TEST3_Farm_Day", 1, true) then
        for _, light in pairs(FindAllOf("DirectionalLightComponent") or {}) do
            if light:IsValid() and light:GetFullName():find("PropNight_Map_TEST3_Farm", 1, true) then
                local ok = pcall(function() light:SetMobility(2) end)  -- EComponentMobility::Movable
                log("Day farm sun set to dynamic shadows: " .. tostring(ok))
            end
        end
    end
    -- One line per map about the character-select scene (restored maps showed an
    -- empty scene): lobby actors, their level and the camera in use.
    local lobbies = {}
    for _, lobby in pairs(FindAllOf("NewLobbyV2_C") or {}) do
        if lobby:IsValid() then
            local where = lobby:GetFullName():match("([%w_]+):PersistentLevel") or "?"
            local okLoc, loc = pcall(function() return lobby:K2_GetActorLocation() end)
            lobbies[#lobbies + 1] = where .. "@" .. (okLoc and vecText(loc) or "?")
        end
    end
    local okView, view = pcall(function() return localController():GetViewTarget() end)
    log("Lobby scene: NewLobbyV2=" .. (#lobbies > 0 and table.concat(lobbies, ", ") or "none")
        .. " viewTarget=" .. (okView and shortName(view) or "?"))
    cleanedWorld = worldId
    if #removed > 0 then
        log("Removed Halloween decoration sublevels: " .. table.concat(removed, ", "))
    end
end
-- Where this game is, for the launcher (revival-presence.txt: "role=host|client|menu"
-- and "server=ip:port"): friends behind the same router share one public address,
-- so the revival server cannot tell from addresses alone which of them is in a game.
local presenceFile = win64 .. "/revival-presence.txt"
local menuSince = nil
local lastPresence = nil
local function writePresence()
    local pc = localController()
    if not pc then return end
    local role = "menu"
    if pc:GetFullName():find("PC_MainMenu_C", 1, true) then
        -- back in the menu for a while: the next game's role is detected again
        -- (detectRole); a join command restarts the wait (the map is loading)
        menuSince = menuSince or os.clock()
        if os.clock() - menuSince > 60 then lanRole, currentServer = nil, nil end
    elseif lanRole == "host" then
        menuSince = nil
        role = "host"
    elseif lanRole == "client" then
        menuSince = nil
        role = "client"
        if not currentServer then
            -- joined from the server browser: GI_Prophunt.ConnectCustomGame keeps the address
            local address = readString(FindFirstOf("GI_Prophunt_C"), "LD_CustomGameAddress")
            if address and address:match("^%d+%.%d+%.%d+%.%d+:%d+$") then currentServer = address end
        end
    end
    local text = "role=" .. role .. "\n" .. (role == "client" and currentServer and ("server=" .. currentServer .. "\n") or "")
    if text == lastPresence then return end
    local file = io.open(presenceFile, "w")
    if file then
        file:write(text)
        file:close()
        lastPresence = text
    end
end
-- End of a match on the host. When a match ends the server already gives the next
-- round's roles (GS_PropHunt.ManageProphuntSlots -> PC.SetIsKiller, which also sets
-- PS.IsKiller), and the end screens read PS.IsKiller of GetPlayerController(0):
-- W_VictoryScreen (GiveCoins) and WBP_EndGameLevel (Init: stats categories). A client
-- gets the new role over the network after its screens are built; on the listen-server
-- host it is already there, so the host who played the killer got the survivor's
-- screens. The host's PlayerState keeps the role it played while the screens are up.
local matchRole = nil
local endScreen = nil
local endScreenWatched = {}
local endScreenClasses = {
    "/Game/Blueprints/MiniLobby/W_VictoryScreen.W_VictoryScreen_C",
    "/Game/Blueprints/MiniLobby/WBP_EndGameLevel.WBP_EndGameLevel_C",
}
-- A map change frees the old world's objects, and UE4SS's IsValid reads an object's own
-- memory to answer: a reference kept across the change read freed memory (client crash,
-- EXCEPTION_ACCESS_VIOLATION in the mod's tick, when the host left the end-of-match screens
-- and the client was sent back to the menu). The current world is read from the engine's
-- viewport (both live as long as the game) at the start of every tick and in the end-screen
-- notification; when it changed, every object kept between ticks is forgotten first and the
-- lists are rebuilt from the live objects (the new world's controller is created during the
-- load, before that tick); later objects come from the creation notifications. (UE4SS 3.0.1's RegisterLoadMapPreHook
-- throws on this game: crash at the first map load.)
local engineRef = nil
local worldKey = nil
local worldCheckLogged = false
local function checkWorld()
    if not (engineRef and engineRef:IsValid()) then engineRef = FindFirstOf("GameEngine") end
    if not engineRef then return end
    local ok, key = pcall(function()
        local world = engineRef.GameViewport.World
        return world:GetFullName() .. "@" .. tostring(world:GetAddress())
    end)
    if not worldCheckLogged then
        worldCheckLogged = true
        log("World change check: " .. (ok and "ok" or tostring(key)))
    end
    if not ok or not key or key == worldKey then return end
    if worldKey then
        -- the new world's own objects were created during the load, before this tick:
        -- the lists are rebuilt from the live objects (one scan per map change)
        controllers = {}
        for _, class in ipairs({ "PC_PropHunt_C", "PC_MainMenu_C" }) do
            for _, pc in pairs(FindAllOf(class) or {}) do track(controllers, pc) end
        end
        loadedClasses = {}
        for _, entry in ipairs(lobbyTracked) do
            entry.objects = {}
            if entry.registered then
                for _, object in pairs(FindAllOf(entry.short) or {}) do track(entry.objects, object) end
            end
        end
        messageBoxes = {}
        if pendingInvite then pendingInvite.dialog = nil end
        slotInitials, rowSlots, rowMarks, rowPlaced, reportWindows = {}, {}, {}, {}, {}
        endScreen = nil
    end
    worldKey = key
end
local function holdMatchRole(widget)
    if lanRole ~= "host" or not matchRole then return end
    local pc = localController()
    local ps = readObject(pc, "PlayerState")
    if not ps then return end
    local played = matchRole == "killer"
    local current = readValue(ps, "IsKiller") == "true"
    local okFirst, first = pcall(function()
        return StaticFindObject("/Script/Engine.Default__GameplayStatics"):GetPlayerController(pc, 0)
    end)
    log(string.format("End screen %s: played %s, PS.IsKiller=%s, GetPlayerController(0) is this player=%s", shortName(widget),
        matchRole, tostring(current), tostring(okFirst and first and first:IsValid() and first:GetAddress() == pc:GetAddress())))
    if current ~= played then
        ps.IsKiller = played
        endScreen = { ps = ps, since = os.clock() }
    elseif endScreen then
        endScreen.since = os.clock()
    end
end
local function watchEndScreens()
    local playing = inMatch()
    if playing and not endScreen then matchRole = localKiller() and "killer" or "survivor" end
    if endScreen and not playing then endScreen.left = true end
    for _, path in ipairs(endScreenClasses) do
        if not endScreenWatched[path] and loadedClass(path) then
            endScreenWatched[path] = true
            NotifyOnNewObject(path, function(widget)
                pcall(checkWorld)
                endScreenAt = os.clock()
                lastEndScreenAt = endScreenAt
                local ok, err = pcall(holdMatchRole, widget)
                if not ok then log("End screen role error: " .. tostring(err)) end
            end)
        end
    end
    if endScreen and (os.clock() - endScreen.since > 30 or (endScreen.left and playing)) then
        -- back to the role the game gave for the next round
        local ok = pcall(function() endScreen.ps.IsKiller = localController().IsKiller end)
        log("End screens done: next round role restored: " .. tostring(ok))
        endScreen = nil
    end
end
-- Ranked progress (MMR, calibration matches, daily tasks): PC_PropHunt.ClientOnEndGame
-- only calls GI.OnMatchEnd when GI.IsMatchmaking is true, which the game sets in
-- ConnectMatchmakingGame ("Find a game") and clears in ConnectCustomGame. A host who
-- created the game, or a friend who joined from an invite, never counted their games.
-- The flag is set during the match only: in the lobby W_MiniLobby.ButtonSwitch enables
-- Start only when it is false (matchmaking games start by themselves), so it is cleared
-- once the end of the match has been handled (victory screen, built by ClientOnEndGame
-- just before GI.OnMatchEnd) and the host's Start button is switched back on.
local matchmakingSet = false
local matchOver = false   -- the match ended; the next one starts once the pawns are gone
local matchPlayedAt = nil   -- this match's start was counted (a victory screen is also built at the start)
-- The match is counted when it starts: PC_PropHunt's game-start event calls
-- GI.DecreaseMmr(GI.MMR_DecreaseOnStart) (MatchesPlayed + 1 and an MMR deposit, given
-- back with the result by GI.OnMatchEnd) only when IsMatchmaking. The flag must stay
-- false in the lobby (with it, Start is disabled and the ready countdown follows the
-- matchmaking rules: one minute, then the game never started), so the mod makes that
-- call itself once the match has begun, sets the flag for GI.OnMatchEnd, and clears it
-- 3 s after the victory screen.
-- Match record for the revival server (Win64/revival-matches.jsonl, sent by the
-- launcher with the player's account): map, length, result, this player's role,
-- character and MMR before/after, and every player's end-of-match stats
-- (GS_PropHunt.HighlightPlayerInformation, EndGamePlayerData).
local matchesFile = win64 .. "/revival-matches.jsonl"
local matchInfo = nil
local highlightFields = {
    name = "Nickname_2_3D137DF24936DB1DAFF0D1A6F131E0DA", killer = "isKiller_5_8EEA3D6E4AFF12E17887298522C8DBD5",
    surv = "CharType_10_7FB6B4ED4269CD4185E5C5AC7CEB5DE9", killerType = "KillerType_13_09BEA465403673844207F3A9B0DE7896",
    damage = "DamageDone_18_294782D84DE8333133BB418A77C93423", kills = "Kills_20_3386BAAF46577BCA0EC8A1809E5677FA",
    assists = "Assists_22_8FD810904D757841F66929B7ADE52BED", objectives = "ObjectivesDone_24_9A56FA6C4DCCB78FB4C67F90A3DABC7D",
    survival = "SurvivalTime_26_0EFFAC77481D4797672F2EB1859B435B", stuns = "Stuns_28_A4B90BCD4D6FE104282A48B469BEC6B5",
    distance = "DistanceTraveled_30_279036494B8BA5FFEEFFDDAA3ABC974D", mvp = "isMVPPlayer_33_9A6A408148C8C0AA0EA00F9FB5A53380",
    mmr = "MMR_63_BF0586DE49217C92F07D2ABA837B0D43",
}
local function jsonValue(v)
    if type(v) == "boolean" then return tostring(v) end
    if type(v) == "number" then return (v == v and v ~= math.huge and v ~= -math.huge) and string.format("%.10g", v) or "null" end
    if v == nil then return "null" end
    if type(v) == "userdata" then
        local ok, text = pcall(function() return v:ToString() end)
        if ok then return jsonString(text) end
        return jsonString(tostring(v))
    end
    return jsonString(v)
end
local function startMatchRecord(gi)
    local ps = readObject(localController(), "PlayerState")
    local killer = localKiller() ~= nil
    matchInfo = {
        startedAt = os.time(), killer = killer,
        character = tonumber(readValue(ps, killer and "KillerChar" or "survChar")),
        mmrBefore = tonumber(readValue(gi, "MMR")), matchesBefore = tonumber(readValue(gi, "MatchesPlayed")),
        map = (localController():GetWorld():GetFullName():match("%.([%w_]+)$")) or "",
        role = lanRole, server = currentServer,
    }
end
local function writeMatchRecord(gi)
    if not matchInfo then return end
    local info = matchInfo
    matchInfo = nil
    local gs = FindFirstOf("GS_PropHunt_C")
    local killerWon = readValue(gs, "IsKillerWin") == "true"
    local players = {}
    pcall(function()
        gs.HighlightPlayerInformation:ForEach(function(_, element)
            local entry = element:get()
            local fields = {}
            for key, field in pairs(highlightFields) do
                local ok, value = pcall(function() return entry[field] end)
                if ok then fields[#fields + 1] = jsonString(key) .. ":" .. jsonValue(value) end
            end
            players[#players + 1] = "{" .. table.concat(fields, ",") .. "}"
        end)
    end)
    local line = string.format('{"map":%s,"role":%s,"server":%s,"killer":%s,"character":%s,"won":%s,"killerWon":%s,'
        .. '"startedAt":%d,"endedAt":%d,"mmrBefore":%s,"mmrAfter":%s,"matchesBefore":%s,"matchesAfter":%s,"players":[%s]}\n',
        jsonString(info.map), jsonValue(info.role), jsonValue(info.server), tostring(info.killer), jsonValue(info.character),
        tostring(info.killer == killerWon), tostring(killerWon), info.startedAt, os.time(), jsonValue(info.mmrBefore),
        jsonValue(tonumber(readValue(gi, "MMR"))), jsonValue(info.matchesBefore), jsonValue(tonumber(readValue(gi, "MatchesPlayed"))),
        table.concat(players, ","))
    local file = io.open(matchesFile, "a")
    if file then file:write(line); file:close() end
    log("Match recorded: " .. #players .. " players, MMR " .. tostring(info.mmrBefore) .. " -> " .. tostring(readValue(gi, "MMR")))
end
-- Role swap diagnostic for the match (5 s and 15 s after the start, every player):
-- each PlayerState's role and pawn as this game sees them, with the pawn's position
-- (a pawn that does not move between the two lines is not replicated here).
local matchPawnLogs = 2
local function matchPawnsDiag()
    local gs = FindFirstOf("GS_PropHunt_C")
    local parts = {}
    pcall(function()
        gs.PlayerArray:ForEach(function(_, element)
            local ps = element:get()
            local okPawn, pawn = pcall(function() return ps:GetPawn() end)
            pawn = okPawn and pawn and pawn:IsValid() and pawn or nil
            local okLoc, loc = pcall(function() return pawn:K2_GetActorLocation() end)
            local okCtl, ctl = pcall(function() return pawn:GetController() end)
            parts[#parts + 1] = string.format("%s killer=%s pawn=%s at %s ctl=%s", readString(ps, "NickNamePS") or "?",
                readValue(ps, "IsKiller"), shortName(pawn), okLoc and loc and vecText(loc) or "?", okCtl and shortName(ctl) or "-")
        end)
    end)
    log("Match pawns (" .. tostring(lanRole) .. "): " .. table.concat(parts, " | "))
end
local function countAsMatchmaking()
    local pc = localController()
    if not pc then return end
    if not (gameInstance and gameInstance:IsValid()) then gameInstance = FindFirstOf("GI_Prophunt_C") end
    if not (gameInstance and gameInstance:IsValid()) then return end
    if pc:GetFullName():find("PC_MainMenu_C", 1, true) then
        -- left the game: the next one starts afresh
        if matchmakingSet then pcall(function() gameInstance:SetIsMatchMaking(false) end) end
        matchmakingSet, matchPlayedAt, endScreenAt = false, nil, nil
        return
    end
    if not lanRole then return end
    if matchOver then
        -- the end screens still show the match's pawns: wait for the lobby
        if not inMatch() then matchOver = false end
        return
    end
    if matchPlayedAt and matchPawnLogs < 2 and os.clock() - matchPlayedAt > (matchPawnLogs == 0 and 5 or 15) then
        matchPawnLogs = matchPawnLogs + 1
        local okPawns, errPawns = pcall(matchPawnsDiag)
        if not okPawns then log("Match pawns error: " .. tostring(errPawns)) end
    end
    if inMatch() and not matchPlayedAt then
        matchPlayedAt = os.clock()
        matchPawnLogs = 0
        local okRecord, errRecord = pcall(startMatchRecord, gameInstance)
        if not okRecord then log("Match record error: " .. tostring(errRecord)) end
        if readValue(gameInstance, "IsMatchmaking") == "false" then
            local ok, err = pcall(function()
                gameInstance:DecreaseMmr(gameInstance.MMR_DecreaseOnStart)
                gameInstance:SetIsMatchMaking(true)
            end)
            matchmakingSet = ok
            log("Match start counted (MMR, calibration " .. tostring(readValue(gameInstance, "MatchesPlayed"))
                .. ", tasks): " .. (ok and "ok" or tostring(err)))
        end
    elseif matchPlayedAt and endScreenAt and endScreenAt > matchPlayedAt and os.clock() - endScreenAt > 3 then
        local okRecord, errRecord = pcall(writeMatchRecord, gameInstance)
        if not okRecord then log("Match record error: " .. tostring(errRecord)) end
        if matchmakingSet then
            local ok = pcall(function() gameInstance:SetIsMatchMaking(false) end)
            log("Match over: matchmaking flag cleared: " .. tostring(ok))
        end
        matchmakingSet, matchPlayedAt, endScreenAt, matchOver = false, nil, nil, true
    end
end
local function runCommand(command)
    if command == "abbey" then executeCommand("open " .. abbey)
    elseif command == "host" then
        lanRole = "host"
        executeCommand("open " .. abbey .. "?listen?port=7777")
    elseif command == "status" then snapshot()
    elseif command == "lobbydump" then
        lastSlotState = nil
        lastSlotCheck = 0
        lobbySlotsDiag()
        local gs = FindFirstOf("GS_PropHunt_C")
        local okFree, free = pcall(function() return gs:IsKillerSlotFree() end)
        log("Killer slot free: " .. tostring(okFree) .. " " .. tostring(free))
    elseif command and command:match("^lua ") then
        -- developer command (test harness only): needs Win64/revival-dev.txt, never distributed
        local dev = io.open(win64 .. "/revival-dev.txt", "r")
        if not dev then log("lua command ignored (no revival-dev.txt)"); return end
        dev:close()
        revivalLog, revivalLocalController, revivalReadValue = log, localController, readValue
        local chunk, compileError = load(command:sub(5), "dev")
        if not chunk then log("lua compile error: " .. tostring(compileError)); return end
        local ok, result = pcall(chunk)
        log("lua: " .. tostring(ok) .. " " .. tostring(result))
    elseif command and command:match("^invite ") then
        showInvite(command)
    elseif command and command:match("^missingmaps") then
        showMissingMaps(command:match("^missingmaps%s+(.-)%s*$"))
    elseif command and command:match("^joinrelay ") then
        -- written by the launcher (invite / join a friend): the friend's game on the
        -- revival relay, whose address the launcher writes to revival-relay.txt at launch
        -- (from the server; online.txt's relay= as a fallback)
        local port = tonumber(command:match("^joinrelay (%d+)$"))
        local relay = nil
        local relayFile = io.open(win64 .. "/revival-relay.txt", "r")
        if relayFile then relay = (relayFile:read("*l") or ""):match("^%s*(%d+%.%d+%.%d+%.%d+)%s*$"); relayFile:close() end
        relay = relay or (online and online.relay and online.relay:match("^%d+%.%d+%.%d+%.%d+$"))
        if not (port and port >= 7800 and port <= 7999 and relay) then
            log("Invalid relay join: " .. command)
        elseif not lanRole and not inMatch() and not (menuWatch.since and os.clock() - menuWatch.since > 5) then
            -- the game is still starting: try again once the menu is ready
            local again = io.open(commandFile, "w")
            if again then again:write(command); again:close() end
        else
            lanRole, menuSince = nil, nil
            currentServer = relay .. ":" .. port
            log("Joining a friend's game on the relay, port " .. port)
            executeCommand("open " .. relay .. ":" .. port)
        end
    elseif command and command:match("^join ") then
        local address = command:sub(6)
        if safeLanAddress(address) then
            lanRole, menuSince = "client", nil
            currentServer = address .. ":7777"
            executeCommand("open " .. address .. ":7777")
        else log("Invalid LAN address") end
    end
end
-- Chairs of the restored maps. The February 2022 levels (day farm, school) place
-- HypnoChairBP actors saved with the components of that time: no InteractionCheckingBox,
-- TraceLocation, AntiStepCollision... (placed actors keep their own component set, as the
-- props did). HypnoChairBP.CanKillerInteract needs the killer inside InteractionCheckingBox,
-- so a carried survivor could never be put on a chair, and the drop, which uses the chair's
-- points, sent the survivor to 0,0,0 and left the killer stuck. The host replaces every
-- chair missing InteractionCheckingBox (and any old TortureChairBP) by a fresh HypnoChairBP
-- at the same place (replicated) and destroys the old one (the destruction of a level
-- actor reaches the clients); a client hides any old chair still there.
local chairWorld, chairWorldSince, chairsDone = nil, 0, false
local replacedChairs = {}   -- destroyed chairs stay listed (IsValid) until garbage collection
local chairClassPath = "/Game/Blueprints/InGame/HypnoChairBP.HypnoChairBP_C"
local function replaceOldChairs()
    if not lanRole then return end
    local pc = localController()
    if not pc or pc:GetFullName():find("PC_MainMenu_C", 1, true) then return end
    local world = pc:GetWorld()
    local worldId = world:GetFullName() .. "@" .. tostring(world:GetAddress())
    if chairWorld ~= worldId then chairWorld, chairWorldSince, chairsDone, replacedChairs = worldId, os.clock(), false, {} end
    if chairsDone or os.clock() - chairWorldSince > 120 then return end
    -- only the February 2022 levels (day farm, school) have incomplete chairs
    if not worldId:find("PropNight_Map_TEST", 1, true) then chairsDone = true; return end
    local old = {}
    for _, chair in pairs(FindAllOf("TortureChairBP_C") or {}) do
        if chair:IsValid() and not chair:GetFullName():find("Default__", 1, true) and not replacedChairs[tostring(chair:GetAddress())] then old[#old + 1] = chair end
    end
    for _, chair in pairs(FindAllOf("HypnoChairBP_C") or {}) do
        if chair:IsValid() and not chair:GetFullName():find("Default__", 1, true) and not replacedChairs[tostring(chair:GetAddress())]
            and not readObject(chair, "InteractionCheckingBox") then
            old[#old + 1] = chair
        end
    end
    if #old == 0 then
        -- the chairs are in sublevels that stream in: wait for them before giving up
        if next(replacedChairs) or os.clock() - chairWorldSince > 60 then chairsDone = true end
        return
    end
    if lanRole ~= "host" then
        for _, chair in ipairs(old) do
            replacedChairs[tostring(chair:GetAddress())] = true
            pcall(function() chair:SetActorHiddenInGame(true) end)
            pcall(function() chair:SetActorEnableCollision(false) end)
        end
        return
    end
    local cls = StaticFindObject(chairClassPath)
    if not (cls and cls:IsValid()) then pcall(LoadAsset, "/Game/Blueprints/InGame/HypnoChairBP"); cls = StaticFindObject(chairClassPath) end
    if not (cls and cls:IsValid()) then log("HypnoChairBP class not found: old chairs kept"); chairsDone = true; return end
    local replaced = 0
    for _, chair in ipairs(old) do
        local ok, err = pcall(function()
            local loc, rot = chair:K2_GetActorLocation(), chair:K2_GetActorRotation()
            local fresh = world:SpawnActor(cls, { X = loc.X, Y = loc.Y, Z = loc.Z }, { Pitch = rot.Pitch, Yaw = rot.Yaw, Roll = rot.Roll })
            if not (fresh and fresh:IsValid()) then error("spawn failed") end
            replacedChairs[tostring(chair:GetAddress())] = true
            chair:K2_DestroyActor()
        end)
        if ok then replaced = replaced + 1 else log("Chair replacement error: " .. tostring(err)) end
    end
    log("Incomplete chairs replaced by a fresh HypnoChairBP: " .. replaced .. "/" .. #old)
end
local function slowTick()
    pollCount = pollCount + 1
    local ok, err = pcall(removeHalloweenSublevels)
    if not ok and cleanedWorld ~= "error" then
        cleanedWorld = "error"
        log("Halloween decoration removal error: " .. tostring(err))
    end
    local file = io.open(commandFile, "r")
    if file then
        local command = file:read("*l")
        file:close()
        os.remove(commandFile)
        local okCommand, errCommand = pcall(runCommand, command)
        if not okCommand then log(tostring(errCommand)) end
    end
    if queuedCommand then
        local command = queuedCommand
        queuedCommand = nil
        local okQueued, errQueued = pcall(runCommand, command)
        if not okQueued then log(tostring(errQueued)) end
    end
    pcall(detectRole)
    if online and lanRole == "host" then
        local pc = localController()
        if pc and not pc:GetFullName():find("PC_MainMenu_C", 1, true) then touchAliveFile() end
    end
    if lanRole then
        local okLan, errLan = pcall(maintainLanSession)
        if not okLan then log("LAN maintenance error: " .. tostring(errLan)) end
    end
    local okChairs, errChairs = pcall(replaceOldChairs)
    if not okChairs then log("Chair replacement error: " .. tostring(errChairs)) end
    local okPresence, errPresence = pcall(writePresence)
    if not okPresence then log("Presence file error: " .. tostring(errPresence)) end
    local okEnd, errEnd = pcall(watchEndScreens)
    if not okEnd then log("End screen watch error: " .. tostring(errEnd)) end
    local okCount, errCount = pcall(countAsMatchmaking)
    if not okCount then log("Matchmaking flag error: " .. tostring(errCount)) end
end
-- One timer drives the mod. UE4SS 3.0.1 runs ExecuteWithDelay callbacks on its own
-- thread, on the game thread's Lua state: every ExecuteInGameThread made there adds
-- a registry reference while the game thread releases others, and the registry ends
-- up corrupted (client crash after a few minutes in the lobby: "Unhandled Exception
-- 0xe06d7363" thrown by UE4SS, "[Lua::Registry::get_function_ref] Ref was not
-- function"). The mod made about 33 of these calls per second in the lobby; now
-- one per tick (4 per second in the lobby, 2 in the menu, 1 in a match), and the
-- timer callback does nothing else.
local tickDelay = 1000
local lastSlowTick = -10
local function gameTick()
    local okWorld, errWorld = pcall(checkWorld)
    if not okWorld then log("World check error: " .. tostring(errWorld)) end
    if os.clock() - lastSlowTick >= 0.9 then
        lastSlowTick = os.clock()
        local ok, err = pcall(slowTick)
        if not ok then log("Tick error: " .. tostring(err)) end
    end
    local ok, err = pcall(fastTick)
    if not ok then log("Lobby tick error: " .. tostring(err)) end
    if lanRole and not inMatch() then tickDelay = 250
    elseif menuWatch.pc and not menuWatch.done then tickDelay = 500
    else tickDelay = 1000 end
end
local function tick()
    ExecuteInGameThread(gameTick)
    ExecuteWithDelay(tickDelay, tick)
end
log("Ready. Host from the menu (Custom Game > Create Game) or with the command file.")
ExecuteWithDelay(10000, tick)
